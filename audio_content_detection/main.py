
import os
import uuid
import math
import openai
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from modelscope.pipelines import pipeline
from modelscope.utils.constant import Tasks
from pydub import AudioSegment

# --- 配置 ---
UPLOAD_DIR = "uploads"
CHUNK_DIR = os.path.join(UPLOAD_DIR, "chunks")
os.makedirs(CHUNK_DIR, exist_ok=True)

# 1. 初始化 FastAPI 和模板
app = FastAPI()
templates = Jinja2Templates(directory="templates")

# 2. 配置本地 LLM (LM Studio)
client = openai.OpenAI(base_url="http://127.0.0.1:1234/v1", api_key="not-needed")
LLM_MODEL = "google/gemma-3-4b"

# 3. 加载语音识别模型
print("正在加载语音识别模型，请稍候...")
try:
    asr_pipeline = pipeline(
        task=Tasks.auto_speech_recognition,
        model='iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch'
    )
    print("语音识别模型加载成功。")
except Exception as e:
    print(f"加载语音识别模型失败: {e}")
    asr_pipeline = None

# --- 音频处理函数 ---
def split_audio_into_chunks(file_path, chunk_length_ms=15000, overlap_ms=1500):
    """使用 pydub 将音频文件分割成带重叠的块"""
    try:
        audio = AudioSegment.from_file(file_path)
        chunks = []
        start_time = 0
        audio_len_ms = len(audio)

        while start_time < audio_len_ms:
            end_time = start_time + chunk_length_ms
            chunk = audio[start_time:end_time]
            chunk_path = os.path.join(CHUNK_DIR, f"chunk_{uuid.uuid4()}.wav")
            chunk.export(chunk_path, format="wav")
            chunks.append(chunk_path)
            
            start_time += (chunk_length_ms - overlap_ms)
            
        return chunks
    except Exception as e:
        print(f"音频分片失败: {e}")
        return []

# --- API 端点 ---

@app.get("/", response_class=HTMLResponse)
async def get_upload_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/process-audio/")
async def process_audio(file: UploadFile = File(...)):
    if not asr_pipeline:
        return JSONResponse(status_code=500, content={"error": "语音识别模型未成功加载，请检查服务日志。"})

    # 1. 保存原始上传文件
    original_file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{file.filename}")
    try:
        with open(original_file_path, "wb") as buffer:
            buffer.write(await file.read())
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"保存文件失败: {e}"})

    # 2. 对长音频进行分片
    print(f"开始对文件进行分片: {original_file_path}")
    audio_chunks = split_audio_into_chunks(original_file_path)
    if not audio_chunks:
        # 清理原始上传文件
        if os.path.exists(original_file_path):
            os.remove(original_file_path)
        return JSONResponse(status_code=500, content={"error": "音频分片失败，请检查文件格式或服务日志。"})

    # 3. 逐个识别分片并拼接结果
    full_transcribed_text = []
    try:
        for i, chunk_path in enumerate(audio_chunks):
            print(f"正在处理分片 {i+1}/{len(audio_chunks)}: {chunk_path}")
            try:
                rec_result = asr_pipeline(input=chunk_path)
                if rec_result and isinstance(rec_result, list) and len(rec_result) > 0:
                    text = rec_result[0].get("text")
                    if text:
                        full_transcribed_text.append(text)
            except Exception as e:
                print(f"分片 {chunk_path} 识别失败: {e}")
            finally:
                if os.path.exists(chunk_path):
                    os.remove(chunk_path) # 清理分片文件
        
        transcribed_text = " ".join(full_transcribed_text)
        if not transcribed_text:
            transcribed_text = "未能识别出任何文本。"
        print(f"完整识别结果: {transcribed_text}")

    finally:
        # 清理原始上传文件
        if os.path.exists(original_file_path):
            os.remove(original_file_path)

    # 4. 调用 LLM 进行分析
    analysis_result = "未能获取分析结果。"
    if transcribed_text and "未能识别" not in transcribed_text:
        try:
            prompt = f'''
你是一位专业的业务分析助手。你的任务是从以下神秘访客的录音文本中，提取关键的业务信息。

请严格按照以下格式输出，如果某项信息不存在，请填写“未提及”。

- **商品规格**: 
- **商品价格**: 
- **有效日期**: 
- **门店编号**: 

---
**录音文本:**
{transcribed_text}
---
'''
            
            completion = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
            )
            analysis_result = completion.choices[0].message.content
            print(f"LLM 分析结果: {analysis_result}")

        except Exception as e:
            print(f"调用本地 LLM 出错: {e}")
            analysis_result = f"调用 LLM 分析时出错: {e}"

    # 5. 返回结果
    return JSONResponse(content={
        "transcribed_text": transcribed_text,
        "analysis_result": analysis_result
    })
