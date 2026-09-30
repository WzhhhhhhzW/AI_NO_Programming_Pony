import json
import os
import sys

# AI 必须由用户填写地址、密钥和模型；不内置服务或凭据。
DEFAULT_API_KEY = ""
DEFAULT_API_BASE_URL = ""
DEFAULT_ENDPOINT_ID = ""
DEFAULT_POWER = 1
POWER = -1

# 运行时配置（只接受用户保存的设置，留空时禁用 AI）
API_KEY = ""
API_BASE_URL = ""
ENDPOINT_ID = ""

_CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "RenesasHorseAI")
_USER_CONFIG_FILE = os.path.join(_CONFIG_DIR, "api_config.json")
os.makedirs(_CONFIG_DIR, exist_ok=True)
USER_CONFIG_FILE = _USER_CONFIG_FILE


def get_api_key():
    return API_KEY


def get_api_base_url():
    return API_BASE_URL


def get_endpoint_id():
    return ENDPOINT_ID


def api_config_error(api_key, base_url, model):
    from urllib.parse import urlsplit
    if not all(isinstance(value,str) and value.strip() for value in (api_key,base_url,model)):
        return "请先在 API 设置中填写 base_url、api_key 和 model；软件没有默认 API。"
    try:
        url=urlsplit(base_url.strip())
        _ = url.port
    except ValueError:
        return "base_url 应为有效的 API 服务地址。"
    if url.scheme not in ("https","http") or not url.hostname or url.username or url.password or url.query or url.fragment:
        return "base_url 应为有效的 API 服务地址。"
    if url.hostname == "platform.deepseek.com":
        return "这是账户管理网页，请填写 DeepSeek API 地址 https://api.deepseek.com。"
    return ""


def get_power():
    return POWER if 0 <= POWER <= 2 else DEFAULT_POWER


def set_power(index):
    globals()["POWER"] = index if isinstance(index,int) and 0 <= index <= 2 else DEFAULT_POWER


def load_user_config():
    globals().update(API_KEY="",API_BASE_URL="",ENDPOINT_ID="")
    if os.path.exists(USER_CONFIG_FILE):
        try:
            with open(USER_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            globals()["API_KEY"] = data.get("api_key", "")
            globals()["API_BASE_URL"] = data.get("api_base_url", "")
            globals()["ENDPOINT_ID"] = data.get("endpoint_id", "")
            set_power(data.get("power", DEFAULT_POWER))
            return True
        except Exception:
            pass
    return False


def save_user_config(api_key="", api_base_url="", endpoint_id="", power=None):
    try:
        with open(USER_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "api_key": api_key,
                "api_base_url": api_base_url,
                "endpoint_id": endpoint_id,
                "power": get_power() if power is None else power,
            }, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


# --------------- workspace / paths persistence ---------------

_WORKSPACE_CONFIG_FILE = os.path.join(_CONFIG_DIR, "workspace_config.json")


def load_workspace_config() -> dict:
    """Load persisted workspace and tool path preferences."""
    cfg = {"workspace_dir": "", "last_project": ""}
    if os.path.exists(_WORKSPACE_CONFIG_FILE):
        try:
            with open(_WORKSPACE_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key in cfg:
                if data.get(key):
                    cfg[key] = data[key]
        except Exception:
            pass
    return cfg


def save_workspace_config(workspace_dir="", last_project=""):
    """Persist workspace directory and last-opened project."""
    try:
        cfg = load_workspace_config()
        if workspace_dir:
            cfg["workspace_dir"] = workspace_dir
        if last_project:
            cfg["last_project"] = last_project
        with open(_WORKSPACE_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False
