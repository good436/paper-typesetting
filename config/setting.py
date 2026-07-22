import os
from pathlib import Path
from dotenv import load_dotenv

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