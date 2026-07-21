import os, json

CONFIG_FILE = "config.json"
_cache = {"mtime": 0, "data": None}

def load_config():
    try:
        current_mtime = os.path.getmtime(CONFIG_FILE)
    except OSError:
        raise FileNotFoundError(f"{CONFIG_FILE} not found. Copy config.example.json to config.json and fill in your settings.")

    if current_mtime != _cache["mtime"]:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            _cache["data"] = json.load(f)
        _cache["mtime"] = current_mtime

    return _cache["data"]
