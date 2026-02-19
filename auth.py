"""Gmail OAuth2 authentication module."""

import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Full access scope required for read / modify / delete
SCOPES = ["https://mail.google.com/"]

TOKEN_FILE = "token.json"
CREDENTIALS_FILE = "credentials.json"


def get_gmail_service():
    """Authenticate and return a Gmail API service instance."""
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        # 저장된 토큰의 스코프가 현재 요구 스코프와 다르면 재인증
        if creds and not all(s in (creds.scopes or []) for s in SCOPES):
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"'{CREDENTIALS_FILE}' not found.\n"
                    "Please follow the README to set up Google API credentials."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)
