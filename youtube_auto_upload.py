import os, json, re, time
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
MAX_RETRIES = 5
RETRIABLE = [500, 502, 503, 504]

def setup_credentials():
    cs = os.getenv("YOUTUBE_CLIENT_SECRETS")
    tk = os.getenv("YOUTUBE_TOKEN")
    if not cs or not tk:
        print("Missing YOUTUBE_CLIENT_SECRETS or YOUTUBE_TOKEN")
        return None
    try:
        json.dump(json.loads(cs), open("client_secrets.json", "w"))
        json.dump(json.loads(tk), open("token.json", "w"))
        return Credentials.from_authorized_user_file("token.json", SCOPES)
    except Exception as e:
        print(f"Credential error: {e}")
        return None

def get_metadata():
    if not os.path.exists("youtube_details.txt"): return None
    try:
        content = open("youtube_details.txt", encoding="utf-8").read()
        t = re.search(r"--- YOUTUBE TITLE ---\n(.*?)\n", content, re.DOTALL)
        d = re.search(r"--- YOUTUBE DESCRIPTION ---\n(.*)", content, re.DOTALL)
        return {
            "title": (t.group(1).strip() if t else "Deal Alert!")[:100],
            "description": d.group(1).strip() if d else "",
            "tags": ["amazon deals", "india", "loot", "budget"],
            "category_id": "22"
        }
    except: return None

def upload_video(path, meta, creds):
    youtube = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {k: meta[k] for k in ["title", "description", "tags", "category_id"]},
        "status": {"privacyStatus": "public"}
    }
    media = MediaFileUpload(path, chunksize=1024*1024, resumable=True, mimetype="video/*")
    print(f"Uploading: {meta['title']}")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response, error, retry = None, None, 0
    while response is None:
        try:
            status, response = request.next_chunk()
            if status: print(f"Progress: {int(status.progress() * 100)}%")
        except HttpError as e:
            if e.resp.status in RETRIABLE:
                error, retry = e, retry + 1
            else: raise e
        except (IOError, OSError) as e:
            error, retry = e, retry + 1
        if error:
            if retry > MAX_RETRIES: raise Exception(f"Failed after {retry} attempts")
            time.sleep(2 ** retry)
            error = None
    print(f"Uploaded! Video ID: {response['id']}")
    return response['id']

def main():
    creds = setup_credentials()
    if not creds: return
    import make_reel
    make_reel.main()
    if not os.path.exists("shorts_deal.mp4"): print("Video not generated."); return
    meta = get_metadata()
    if not meta: print("No metadata."); return
    try:
        upload_video("shorts_deal.mp4", meta, creds)
    except Exception as e: print(f"Upload failed: {e}")
    finally:
        for f in ["client_secrets.json", "token.json", "shorts_deal.mp4", "youtube_details.txt"]:
            if os.path.exists(f):
                try: os.remove(f)
                except: pass

if __name__ == "__main__":
    main()
