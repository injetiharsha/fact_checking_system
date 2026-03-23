import os
from dotenv import load_dotenv

# Load .env from project root
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")


def _read_env_value(env_path: str, key: str):
    try:
        with open(env_path, "r", encoding="utf-8-sig") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                name, value = line.split("=", 1)
                if name.strip() == key:
                    return value.strip()
    except OSError:
        return None
    return None


load_dotenv(ENV_PATH, override=True)

NEWS_API_KEY = os.getenv("NEWS_API_KEY") or _read_env_value(ENV_PATH, "NEWS_API_KEY")

if NEWS_API_KEY:
    NEWS_API_KEY = NEWS_API_KEY.strip()

if not NEWS_API_KEY:
    raise ValueError(f"NEWS_API_KEY not found in environment variables or {ENV_PATH}")
