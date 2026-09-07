import os, json

CONFIG_FILE = "config.json"
EXAMPLE_FILE = "config.example.json"
_cache = {"mtime": 0, "data": None}

def load_config():
    path = CONFIG_FILE if os.path.exists(CONFIG_FILE) else EXAMPLE_FILE
    try:
        current_mtime = os.path.getmtime(path)
    except OSError:
        raise FileNotFoundError(f"Neither {CONFIG_FILE} nor {EXAMPLE_FILE} found. Copy config.example.json to config.json.")

    if current_mtime != _cache["mtime"]:
        with open(path, encoding="utf-8") as f:
            _cache["data"] = json.load(f)
        _cache["mtime"] = current_mtime

    return _cache["data"]
