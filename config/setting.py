import os
from pathlib import Path
from dotenv import load_dotenv
import threading

# 线程本地存储 — 每个用户可以用自己的 API Key
_local = threading.local()

def set_user_api_key(key: str):
    """设置当前线程的用户 API Key"""
    _local.user_api_key = key

def get_user_api_key() -> str:
    """获取当前线程的用户 API Key，如果用户没填则用默认的"""
    return getattr(_local, 'user_api_key', None) or DEEPSEEK_API_KEY

# 加载 .env 文件（项目根目录）
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# DeepSeek 模型配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

# 向量库配置
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# 文件路径
INPUT_DIR = "data/input"
OUTPUT_DIR = "data/output"

# 项目根目录
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)