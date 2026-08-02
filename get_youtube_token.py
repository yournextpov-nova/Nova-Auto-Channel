"""
RUN THIS ONCE, ON YOUR OWN COMPUTER (not in GitHub Actions).

It opens a browser, asks you to log into the YouTube channel you want
to automate, and prints a refresh token. Paste that refresh token into
your GitHub repo secrets as YT_REFRESH_TOKEN and you'll never need to
run this again.

Prerequisites:
1. Go to https://console.cloud.google.com/ -> create a project
2. Enable "YouTube Data API v3"
3. Create OAuth credentials -> Application type: "Desktop app"
4. Download the JSON, save it next to this file as client_secret.json
"""
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
creds = flow.run_local_server(port=0)

print("\n\nSave these as GitHub repo secrets:\n")
print("YT_CLIENT_ID     =", creds.client_id)
print("YT_CLIENT_SECRET =", creds.client_secret)
print("YT_REFRESH_TOKEN =", creds.refresh_token)
