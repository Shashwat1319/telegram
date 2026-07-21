import os, json, logging, glob

log = logging.getLogger(__name__)


def _cleanup_tmp(dir_path):
    for f in glob.glob(os.path.join(dir_path, "*.tmp")):
        try:
            os.remove(f)
        except OSError:
            pass


def load_json(path, default=None, encoding="utf-8"):
    if default is None:
        default = {}
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding=encoding) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        log.warning("Invalid JSON in %s: %s", path, e)
        return default
    except Exception as e:
        log.warning("Failed to read %s: %s", path, e)
        return default


def save_json(path, data, encoding="utf-8"):
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding=encoding) as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        return True
    except Exception as e:
        log.error("Failed to write %s: %s", path, e)
        return False
