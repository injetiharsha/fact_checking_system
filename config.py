import os
import re
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


def _parse_env_list(raw):
    if not raw:
        return []
    parts = [part.strip() for part in re.split(r"[\r\n,]+", str(raw)) if part.strip()]
    seen = []
    for part in parts:
        if part not in seen:
            seen.append(part)
    return seen


load_dotenv(ENV_PATH, override=True)

NEWS_API_KEY = os.getenv("NEWS_API_KEY") or _read_env_value(ENV_PATH, "NEWS_API_KEY")
if NEWS_API_KEY:
    NEWS_API_KEY = NEWS_API_KEY.strip()

NEWS_API_KEYS = _parse_env_list(
    os.getenv("NEWS_API_KEYS") or _read_env_value(ENV_PATH, "NEWS_API_KEYS") or NEWS_API_KEY
)

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY") or _read_env_value(ENV_PATH, "TAVILY_API_KEY")
if TAVILY_API_KEY:
    TAVILY_API_KEY = TAVILY_API_KEY.strip()

TAVILY_API_KEYS = _parse_env_list(
    os.getenv("TAVILY_API_KEYS") or _read_env_value(ENV_PATH, "TAVILY_API_KEYS") or TAVILY_API_KEY
)
