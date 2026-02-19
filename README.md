# Gmail Cleaner

Gmail 받은편지함을 대화형 CLI로 정리하는 도구입니다.
Google Gmail API를 사용하며, 삭제 전 미리보기(dry-run)를 지원합니다.

---

## 기능

| 기능 | 설명 |
|------|------|
| 발신자별 삭제 | 특정 이메일 주소/도메인의 메일 전체 삭제 |
| 키워드 검색 삭제 | 제목·본문·Gmail 검색어 기반 삭제 |
| 오래된 메일 삭제 | N일 이상 된 메일 삭제 |
| 프로모션 삭제 | 프로모션 카테고리 전체 삭제 |
| 소셜 삭제 | 소셜 카테고리 전체 삭제 |
| 읽은 메일 보관 | 받은편지함의 읽은 메일을 보관(아카이브) |
| 받은편지함 통계 | 카테고리별 메일 개수 확인 |
| 상위 발신자 분석 | 가장 많은 메일을 보낸 발신자 TOP 20 |

---

## 사전 준비: Google API 인증 설정

### 1. Google Cloud 프로젝트 생성

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 새 프로젝트 생성 (예: `gmail-cleaner`)
3. **APIs & Services > Library** 에서 **Gmail API** 검색 후 활성화

### 2. OAuth 2.0 자격증명 생성

1. **APIs & Services > Credentials** 이동
2. **Create Credentials > OAuth client ID** 클릭
3. Application type: **Desktop app** 선택
4. 생성된 JSON 파일을 다운로드
5. 파일 이름을 `credentials.json`으로 변경
6. 프로젝트 루트 디렉토리에 배치

> **주의:** `credentials.json`과 `token.json`은 절대 git에 커밋하지 마세요.
> `.gitignore`에 이미 포함되어 있습니다.

### 3. OAuth 동의 화면 설정

1. **APIs & Services > OAuth consent screen**
2. User type: **External** 선택
3. 앱 이름, 이메일 입력 후 저장
4. **Test users** 에 본인 Gmail 계정 추가

---

## 설치

```bash
# 저장소 클론
git clone <repo-url>
cd ai-lab-gmail-cleaner

# 가상 환경 생성 (권장)
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

---

## 사용법

### 기본 실행 (실제 삭제)

```bash
python gmail_cleaner.py
```

처음 실행 시 브라우저에서 Google 계정 인증을 요청합니다.
인증 후 `token.json`이 생성되며, 이후 실행부터는 자동 인증됩니다.

### Dry Run 모드 (삭제 없이 미리보기)

```bash
python gmail_cleaner.py --dry-run
```

실제 삭제 없이 몇 개의 메일이 삭제될지 미리 확인할 수 있습니다.

---

## 메뉴 예시

```
╭─ Gmail Cleaner  LIVE MODE ──────────────────────────╮
│  1    Delete emails from a specific sender           │
│  2    Delete emails by keyword / query               │
│  3    Delete emails older than N days                │
│  4    Delete all Promotion emails                    │
│  5    Delete all Social emails                       │
│  6    Archive all read inbox emails                  │
│  7    Show inbox statistics                          │
│  8    Show top senders                               │
│  q    Quit                                           │
╰──────────────────────────────────────────────────────╯
```

---

## Gmail 검색 쿼리 예시 (메뉴 2번)

| 검색어 | 설명 |
|--------|------|
| `from:noreply@example.com` | 특정 발신자 |
| `subject:광고` | 제목에 "광고" 포함 |
| `older_than:2y` | 2년 이상 된 메일 |
| `has:attachment larger:10M` | 10MB 이상 첨부 |
| `label:unsubscribe` | 수신거부 라벨 |
| `is:read in:inbox` | 받은편지함의 읽은 메일 |

---

## 프로젝트 구조

```
ai-lab-gmail-cleaner/
├── gmail_cleaner.py    # 메인 CLI 스크립트
├── auth.py             # Google OAuth2 인증 모듈
├── requirements.txt    # Python 의존성
├── .gitignore          # credentials.json, token.json 등 제외
└── README.md
```

---

## 주의사항

- 삭제된 메일은 Gmail 휴지통으로 이동합니다 (30일 후 영구 삭제).
- Gmail API에는 사용량 제한이 있습니다. 대량 삭제 시 잠시 대기 후 재시도하세요.
- 처음에는 반드시 `--dry-run` 모드로 테스트하세요.
