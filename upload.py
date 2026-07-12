from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def authenticate():
    flow = InstalledAppFlow.from_client_secrets_file(
        "client_secret.json", SCOPES)
    creds = flow.run_local_server(port=0)
    return build("youtube", "v3", credentials=creds)

def upload_video(file, title, description, tags):
    youtube = authenticate()

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": "22"  # People & Blogs
            },
            "status": {
                "privacyStatus": "public"
            }
        },
        media_body=MediaFileUpload(file)
    )

    response = request.execute()
    print("Uploaded:", response["id"])

upload_video(
    "final_output.mp4",
    "Signal 0049 // Pattern Detected",
    "Unusual signal patterns detected. No known origin.",
    ["signal", "pattern", "noise", "analysis"]
)