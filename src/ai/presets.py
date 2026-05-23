"""厂商预设：选厂商即可自动填 base_url 与默认 model。"""
from __future__ import annotations


PRESETS: dict[str, dict[str, str]] = {
    "OpenAI": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
    },
    "DeepSeek": {
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
    },
    "智谱": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-flash",
    },
    "通义": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-turbo",
    },
    "月之暗面": {
        "base_url": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-8k",
    },
    "火山方舟": {
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "model": "",
    },
    "Ollama 本地": {
        "base_url": "http://localhost:11434/v1",
        "model": "qwen2.5:3b",
    },
}


MODEL_PLACEHOLDERS: dict[str, str] = {
    "火山方舟": "请填接入点 ID（ep-xxxxxxxx），不是模型名",
}


DEFAULT_MODEL_PLACEHOLDER = "如 gpt-4o-mini"


PROVIDER_NAMES = list(PRESETS.keys())
