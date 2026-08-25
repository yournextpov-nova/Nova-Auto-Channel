"""
Uploads the finished video to YouTube using a stored OAuth refresh
token (generated once via get_youtube_token.py). No browser login
needed on subsequent/automated runs.
"""
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError


def get_youtube_client():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    return build("youtube", "v3", credentials=creds)


def upload_video(video_path: str, title: str, description: str,
                  tags: list[str], category_id: str = "1",
                  privacy_status: str = "public", thumbnail_path: str | None = None):
    youtube = get_youtube_client()
    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags,
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": True,
            "containsSyntheticMedia": True,
        },
    }
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploaded {int(status.progress() * 100)}%")
    video_id = response["id"]
    print("Upload complete. Video ID:", video_id)

    if thumbnail_path and os.path.exists(thumbnail_path):
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path),
            ).execute()
            print("Custom thumbnail set.")
        except HttpError as e:
            # Custom thumbnails require a phone-verified YouTube channel.
            # Don't fail the whole run over this - the video itself is
            # already uploaded successfully at this point.
            print(f"Could not set custom thumbnail (video still uploaded fine): {e}")

    return video_id
