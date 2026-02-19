"""Gmail OAuth2 authentication module."""

import json
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Full access scope required for read / modify / delete
SCOPES = ["https://mail.google.com/"]

TOKEN_FILE = "token.json"
CREDENTIALS_FILE = "credentials.json"


def _token_has_required_scopes() -> bool:
    """token.json에 저장된 스코프가 현재 SCOPES를 모두 포함하는지 확인합니다."""
    try:
        with open(TOKEN_FILE) as f:
            data = json.load(f)
        stored = data.get("scopes") or []
        return all(s in stored for s in SCOPES)
    except Exception:
        return False


def get_gmail_service():
    """Authenticate and return a Gmail API service instance."""
    creds = None

    if os.path.exists(TOKEN_FILE):
        if _token_has_required_scopes():
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        else:
            # 스코프 불일치: 토큰 삭제 후 재인증
            os.remove(TOKEN_FILE)
            print("인증 권한이 변경되었습니다. 브라우저에서 재인증을 진행합니다...")

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
