import os
import sys
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Scope required for uploading videos to YouTube
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = "token.pickle"
CLIENT_SECRET_FILE = "client_secret.json"

def get_authenticated_service():
    credentials = None
    
    # Load previously saved token if it exists
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "rb") as token:
                credentials = pickle.load(token)
        except Exception as e:
            print(f"Error loading saved token: {e}")
            
    # If there are no (valid) credentials, let the user log in.
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            print("Refreshing expired credentials...")
            try:
                credentials.refresh(Request())
            except Exception as e:
                print(f"Error refreshing credentials: {e}")
                credentials = None
                
        if not credentials:
            print("Initiating OAuth flow... Please approve in your web browser.")
            if not os.path.exists(CLIENT_SECRET_FILE):
                raise FileNotFoundError(f"Missing client secrets file: {CLIENT_SECRET_FILE}")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            # Use local server to authenticate. This will open a browser window.
            credentials = flow.run_local_server(port=0)
            
        # Save credentials for the next run
        try:
            with open(TOKEN_FILE, "wb") as token:
                pickle.dump(credentials, token)
            print("Credentials saved successfully.")
        except Exception as e:
            print(f"Error saving token: {e}")
            
    return build("youtube", "v3", credentials=credentials)

def upload_short(video_path: str, title: str, description: str, privacy_status: str = "public") -> bool:
    """Uploads a video to YouTube as a Short (automatically detected by aspect ratio and #shorts tag)."""
    if not os.path.exists(video_path):
        print(f"Error: Video file not found at {video_path}")
        return False
        
    print(f"Connecting to YouTube API...")
    try:
        youtube = get_authenticated_service()
    except Exception as e:
        print(f"Failed to authenticate: {e}")
        return False

    print(f"Preparing upload for: {video_path}...")
    
    # YouTube Shorts are identified by having #Shorts in description/title
    if "#shorts" not in description.lower() and "#shorts" not in title.lower():
        description += "\n\n#shorts"
        
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": "24", # 24 is Entertainment, suitable for horror channels
            "tags": ["horror", "story", "shorts", "scary", "ghost"]
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False
        }
    }
    
    # Perform the upload
    media = MediaFileUpload(video_path, chunksize=1024*1024, resumable=True)
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )
    
    print("Uploading file... Please wait.")
    response = None
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                print(f"Uploaded: {int(status.progress() * 100)}%")
        except Exception as e:
            print(f"An error occurred during chunk upload: {e}")
            return False
            
    print("\n[SUCCESS] Video uploaded successfully!")
    print(f"Video ID: {response.get('id')}")
    yt_url = f"https://youtube.com/shorts/{response.get('id')}"
    print(f"Watch URL: {yt_url}")
    return yt_url

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python uploader.py <video_path> [title] [description]")
        sys.exit(1)
        
    path = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else "A Whispering Horror | Part 1"
    desc = sys.argv[3] if len(sys.argv) > 3 else "Follow and subscribe for the next part. #shorts #horror"
    
    upload_short(path, title, desc)
