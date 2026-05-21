import os
import json
import sys
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from dotenv import load_dotenv

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/youtube"]

CLIENT_SECRETS_FILE = os.path.join(
    os.environ.get("USERPROFILE", ""),
    "OneDrive", "Documents", "Desktop", "YouTube", "client_secrets.json"
)
TOKEN_FILE = "yt_banner_token.json"
BANNER_PATH = "channel_banner_processed.png"


def get_credentials():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRETS_FILE):
                print(f"[ERROR] client_secrets.json not found at:\n  {CLIENT_SECRETS_FILE}")
                sys.exit(1)
            print("\n[Auth] Opening browser for Google Sign-In...")
            print("IMPORTANT: Select the Deals/Budget channel account!\n")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0, open_browser=True)

        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        print(f"[Auth] Token saved.")

    return creds


def update_channel_banner(creds):
    if not os.path.exists(BANNER_PATH):
        print(f"[ERROR] Banner image not found at: {BANNER_PATH}")
        return

    youtube = build("youtube", "v3", credentials=creds)

    # 1. Get channel ID and existing settings
    resp = youtube.channels().list(part="id,snippet,brandingSettings", mine=True).execute()
    if not resp.get("items"):
        print("[ERROR] No channel found.")
        return

    ch = resp["items"][0]
    channel_id = ch["id"]
    channel_title = ch["snippet"]["title"]
    brandingSettings = ch.get("brandingSettings", {})
    safe_title = channel_title.encode('ascii', 'ignore').decode('ascii')
    print(f"[INFO] Found channel: '{safe_title}' (ID: {channel_id})")

    # 2. Upload banner image to YouTube
    print(f"[INFO] Uploading banner image: {BANNER_PATH}...")
    media = MediaFileUpload(BANNER_PATH, mimetype="image/png", resumable=True)
    insert_request = youtube.channelBanners().insert(media_body=media)
    
    insert_response = None
    while insert_response is None:
        status, insert_response = insert_request.next_chunk()
        if status:
            print(f"[Upload] Banner upload progress: {int(status.progress() * 100)}%")

    banner_url = insert_response["url"]
    print(f"[SUCCESS] Banner uploaded. URL: {banner_url}")

    # 3. Update channel brandingSettings with the uploaded banner URL
    print(f"[INFO] Updating channel brandingSettings...")
    if "image" not in brandingSettings:
        brandingSettings["image"] = {}
    brandingSettings["image"]["bannerExternalUrl"] = banner_url

    youtube.channels().update(
        part="brandingSettings",
        body={
            "id": channel_id,
            "brandingSettings": brandingSettings
        }
    ).execute()

    print(f"[SUCCESS] YouTube Channel Banner updated successfully for '{safe_title}'!")


def main():
    creds = get_credentials()
    try:
        update_channel_banner(creds)
    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)


if __name__ == "__main__":
    main()
