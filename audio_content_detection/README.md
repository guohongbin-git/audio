# 录音内容智能检测系统

[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/) [![FastAPI](https://img.shields.io/badge/Framework-FastAPI-green.svg)](https://fastapi.tiangolo.com/) [![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) [![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](http://makeapullrequest.com)

这是一个基于语音识别（ASR）和大型语言模型（LLM）的Web应用，用于自动转写长音频文件并从中提取结构化信息。

用户可以上传任意格式的音频文件，系统会将其自动转写为文字，并调用本地运行的Gemma-3模型，根据预设的模板（商品规格、价格、有效期、门店编号）提取关键业务信息。

## 功能特性

- **前端音频转换**: 无论用户上传 MP3, M4A, 还是高采样率的 WAV，前端都会利用 **Web Audio API** 在浏览器本地将其无损转换为 **16kHz 单声道 WAV** 格式，确保后端模型能正确处理。
- **长音频分片处理**: 后端使用 `pydub` 库自动将长音频切割为带有重叠的15秒短音频片段，解决了ASR模型无法直接处理长语音的问题。
- **语音转文字**: 使用 **ModelScope** 上的 **Paraformer (paraformer-large-asr-nat-zh-cn-16k-common-vocab8404-pytorch)** 模型进行高效、准确的中文语音识别。模型会在首次运行时自动从 ModelScope 下载。
- **LLM 信息提取**: 调用本地运行的 **Gemma-3** 模型（通过 LM Studio 提供的 OpenAI 兼容 API），根据动态指令（Prompt）从识别文本中提取非结构化信息。
- **异步 Web 框架**: 基于 **FastAPI** 和 **Uvicorn** 构建，性能高效，代码简洁。

## 技术栈

- **后端**: Python, FastAPI, Uvicorn
- **前端**: HTML, CSS, JavaScript (Fetch API, Web Audio API)
- **语音识别**: ModelScope, Paraformer
- **LLM**: Google Gemma-3 (本地部署)
- **音频处理**: Pydub, FFmpeg
- **依赖管理**: uv

## 项目结构

```
audio_content_detection/
├── main.py              # FastAPI 后端应用主入口
├── requirements.txt     # Python 依赖列表
├── README.md            # 项目说明文档
├── .gitignore           # Git 忽略文件配置
├── templates/           # 存放 HTML 模板文件
│   └── index.html       # 上传页面
└── uploads/             # 存放用户上传及处理过程中的临时音频文件
    └── chunks/          # 存放音频分片后的临时文件
```

## 安装与运行

**前提条件:**

1.  **Python**: 建议使用 **Python 3.12.7** (项目当前开发和测试环境版本)。最低要求为 Python 3.9+。
2.  **FFmpeg**: 必须已安装并配置在系统 PATH 中。 `pydub` 依赖此工具进行音频处理。
    -   *macOS*: `brew install ffmpeg`
    -   *Linux*: `sudo apt install ffmpeg`
    -   *Windows*: 从 [https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/) 下载并解压，将 `bin` 目录添加到系统 PATH 环境变量中。
3.  **LM Studio (或兼容的本地LLM服务)**: 确保服务正在运行，并且已加载 `google/gemma-3-4b` 模型。API服务需在 `http://127.0.0.1:1234` 上可用。

**安装步骤:**

1.  克隆本仓库:
    ```bash
    git clone <your-repo-url>
    cd audio_content_detection
    ```

2.  使用 `uv` 安装依赖。此命令会从 ModelScope 的镜像下载必要的音频处理库：
    ```bash
    uv pip install -r requirements.txt -f https://modelscope.oss-cn-beijing.aliyuncs.com/releases/repo.html
    ```
    **注意**: 如果上述命令因网络问题导致下载失败，可以尝试使用国内镜像源加速下载，例如阿里云镜像：
    ```bash
    uv pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ -f https://modelscope.oss-cn-beijing.aliyuncs.com/releases/repo.html
    ```
    或者使用清华源：
    ```bash
    uv pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/ -f https://modelscope.oss-cn-beijing.aliyuncs.com/releases/repo.html
    ```

**运行服务:**

1.  使用 `uvicorn` 启动应用:
    ```bash
    uvicorn main:app --reload
    ```
    首次运行时，程序会自动从 ModelScope 下载 Paraformer 模型，可能需要几分钟时间。如果模型下载速度较慢或失败，可以检查网络连接，或考虑配置代理。

2.  当终端显示 `Uvicorn running on http://127.0.0.1:8000` 时，在浏览器中打开 [http://127.0.0.1:8000](http://127.0.0.1:8000) 即可开始使用。

## ASR 模型说明

本项目使用的 ASR 模型为:
- **模型名称**: Paraformer Large
- **模型ID**: `iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch`
- **来源**: [ModelScope (魔搭)](https://modelscope.cn/models/iic/speech_paraformer-large_asr_nat-zh-cn-16k-common-vocab8404-pytorch/summary)
- **语言**: 中文
- **采样率**: 16kHz
- **自动下载**: 模型会在首次运行应用时由 `modelscope` 库自动下载并缓存到本地（通常在 `~/.cache/modelscope/hub` 目录下），无需手动干预。