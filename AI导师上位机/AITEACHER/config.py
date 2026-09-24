import json
import os
import sys

# 默认配置（系统预设）
DEFAULT_API_KEY = "sk-l8ds2kYjOLrHjlHeK8k5zLgx4f1Sef13qRpgrH08xCAkUTOg"
DEFAULT_API_BASE_URL = "https://api.openai-proxy.org/v1"
DEFAULT_ENDPOINT_ID = "deepseek-v3.2"

# agent（Claude Agent SDK）走 Anthropic 原生协议，和上面的 OpenAI 端点不是
# 同一个路径：代理站把它挂在 /anthropic 下，而不是 /v1。
DEFAULT_ANTHROPIC_BASE_URL = "https://api.openai-proxy.org/anthropic"
# 三挡能力档位，对应 API 设置里那个滑块。界面上不出现型号名，只有左中右。
#   左  改个延时数值够用，最快最便宜
#   中  默认。跨几个文件加一条链路这种活要它才稳（实测 haiku 加不出"后退"）
#   右  现场兜底，一轮改码实测约 $0.4，日常开着太贵
POWER_MODELS = ("claude-haiku-4-5", "claude-sonnet-5", "claude-opus-5")
DEFAULT_POWER = 1
POWER = -1              # 运行时由用户配置覆盖；-1 = 没设过，用默认

# 运行时配置（可由 UI 动态覆盖，留空则使用默认值）
API_KEY = ""
API_BASE_URL = ""
ENDPOINT_ID = ""

_CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "RenesasHorseAI")
_USER_CONFIG_FILE = os.path.join(_CONFIG_DIR, "api_config.json")
os.makedirs(_CONFIG_DIR, exist_ok=True)
USER_CONFIG_FILE = _USER_CONFIG_FILE


def get_api_key():
    return API_KEY if API_KEY else DEFAULT_API_KEY


def get_api_base_url():
    return API_BASE_URL if API_BASE_URL else DEFAULT_API_BASE_URL


def get_endpoint_id():
    return ENDPOINT_ID if ENDPOINT_ID else DEFAULT_ENDPOINT_ID


def get_anthropic_base_url():
    """agent 用的 Anthropic 协议端点。

    用户在 API 设置里填的是 OpenAI 端点（.../v1）。同一个代理站的
    Anthropic 协议在 .../anthropic，所以这里做一次换算；换算不出来
    （用了别的服务商）就退回默认值。
    """
    url = (API_BASE_URL or "").rstrip("/")
    if url.endswith("/v1"):
        return url[: -len("/v1")] + "/anthropic"
    if url.endswith("/anthropic"):
        return url
    return DEFAULT_ANTHROPIC_BASE_URL


def get_power():
    """当前档位下标 0/1/2。越界或没设过都退回默认。"""
    return POWER if 0 <= POWER < len(POWER_MODELS) else DEFAULT_POWER


def set_power(index: int):
    globals()["POWER"] = index if 0 <= index < len(POWER_MODELS) else DEFAULT_POWER


def get_agent_model():
    return POWER_MODELS[get_power()]


def get_edit_model():
    return POWER_MODELS[get_power()]


def load_user_config():
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
