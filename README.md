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

## 1단계 - 사전 준비

### Python 설치 확인

Python 3.10 이상이 필요합니다.

```powershell
python --version
```

설치되어 있지 않다면 [python.org](https://www.python.org/downloads/)에서 최신 버전을 다운로드합니다.
설치 시 반드시 **"Add Python to PATH"** 체크박스를 체크하세요.

### Git 설치 확인

```powershell
git --version
```

설치되어 있지 않다면 [git-scm.com](https://git-scm.com/downloads)에서 다운로드합니다.

---

## 2단계 - Google Cloud Console 설정

Gmail API를 사용하기 위해 Google에서 인증 키를 발급받아야 합니다.
아래 순서대로 진행하세요.

### ① Google Cloud Console 접속

1. [https://console.cloud.google.com](https://console.cloud.google.com) 접속
2. 사용하려는 Gmail 계정으로 로그인

### ② 새 프로젝트 생성

1. 상단 헤더의 프로젝트 선택 드롭다운 클릭
2. 오른쪽 상단 **"새 프로젝트"** 클릭
3. 프로젝트 이름 입력 (예: `gmail-cleaner`) → **"만들기"** 클릭
4. 생성 완료 후 해당 프로젝트가 선택된 상태인지 확인

### ③ Gmail API 활성화

1. 왼쪽 메뉴 → **"API 및 서비스"** → **"라이브러리"** 클릭
2. 검색창에 `Gmail API` 입력 후 검색
3. **Gmail API** 카드 클릭
4. **"사용 설정"** 버튼 클릭
5. 활성화 완료 후 "관리" 버튼이 표시되면 성공

### ④ OAuth 동의 화면 설정

1. 왼쪽 메뉴 → **"API 및 서비스"** → **"OAuth 동의 화면"** 클릭
2. User Type: **"외부(External)"** 선택 → **"만들기"** 클릭
3. 앱 정보 입력:
   - 앱 이름: `gmail-cleaner` (임의로 입력 가능)
   - 사용자 지원 이메일: 본인 Gmail 주소 선택
   - 개발자 연락처 이메일: 본인 Gmail 주소 입력
4. **"저장 후 계속"** 클릭 → 범위(Scopes) 페이지는 그대로 → **"저장 후 계속"** 클릭
5. 테스트 사용자 페이지에서 **"+ ADD USERS"** 클릭
6. 본인 Gmail 주소를 입력 후 **"추가"** → **"저장 후 계속"** 클릭

> **왜 테스트 사용자를 추가해야 하나요?**
> 앱이 Google 검증을 받지 않은 상태(테스트 모드)이므로,
> 등록된 계정만 인증이 허용됩니다. 본인 계정을 추가하면 정상 사용 가능합니다.

### ⑤ OAuth 자격증명 생성 및 credentials.json 다운로드

1. 왼쪽 메뉴 → **"API 및 서비스"** → **"사용자 인증 정보"** 클릭
2. 상단 **"+ 사용자 인증 정보 만들기"** → **"OAuth 클라이언트 ID"** 선택
3. 애플리케이션 유형: **"데스크톱 앱"** 선택
4. 이름 입력 (예: `gmail-cleaner-desktop`) → **"만들기"** 클릭
5. 생성 완료 팝업에서 **"JSON 다운로드"** 버튼 클릭
6. 다운로드된 파일 이름을 정확히 `credentials.json`으로 변경
7. 이 파일을 프로젝트 폴더(`C:\Projects\ai-lab-gmail-cleaner\`)에 복사

> **주의:** `credentials.json`과 `token.json`은 절대 git에 커밋하지 마세요.
> 이 파일에는 개인 API 키가 포함되어 있습니다. `.gitignore`에 이미 설정되어 있습니다.

---

## 3단계 - 설치

PowerShell 또는 명령 프롬프트(cmd)를 열고 아래 순서대로 실행합니다.

```powershell
# 1. 프로젝트 폴더로 이동
cd C:\Projects\ai-lab-gmail-cleaner

# 2. 가상 환경 생성 (프로젝트 전용 Python 환경, 최초 1회만)
python -m venv venv

# 3. 가상 환경 활성화
venv\Scripts\activate
# 프롬프트 앞에 (venv) 가 표시되면 활성화 성공

# 4. 의존성 패키지 설치
pip install -r requirements.txt
```

> **가상 환경이란?**
> 프로젝트마다 독립된 Python 패키지 환경을 만들어 충돌을 방지합니다.
> 매번 실행 전 `venv\Scripts\activate`로 활성화해야 합니다.

---

## 4단계 - 실행

### 처음 실행 시 Google 인증

```powershell
# 가상 환경 활성화 (이미 활성화되어 있으면 생략)
venv\Scripts\activate

# 실행
python gmail_cleaner.py
```

1. 브라우저가 자동으로 열리며 Google 로그인 화면이 표시됩니다.
2. Gmail 계정으로 로그인합니다.
3. **"앱이 확인되지 않았습니다"** 경고가 표시되면 → **"고급"** 클릭 → **"gmail-cleaner(안전하지 않음)으로 이동"** 클릭
   - 이 경고는 Google 검증을 받지 않은 개인 앱이므로 정상입니다.
4. Gmail 권한 허용 화면에서 **"계속"** 클릭
5. 인증 완료 후 `token.json` 파일이 자동 생성됩니다.
   - 이후 실행부터는 브라우저 인증 없이 자동 로그인됩니다.

### Dry Run 모드 (삭제 없이 미리보기)

처음 사용할 때는 반드시 dry-run 모드로 먼저 테스트하세요.
실제로 메일을 삭제하지 않고, 몇 개가 삭제될지 미리 확인할 수 있습니다.

```powershell
python gmail_cleaner.py --dry-run
```

### 실제 실행 (메일 삭제/아카이브)

```powershell
python gmail_cleaner.py
```

---

## 5단계 - 메뉴 사용 방법

실행하면 아래와 같은 메뉴가 표시됩니다.

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

### 메뉴별 사용 방법

#### 1 - 특정 발신자의 메일 전체 삭제

뉴스레터, 광고 메일을 보내는 특정 주소의 메일을 한 번에 삭제합니다.

```
Enter sender email or domain: newsletter@example.com
```

- 이메일 전체 주소 입력: `noreply@github.com`
- 도메인만 입력해도 됩니다: `@linkedin.com`

#### 2 - 키워드/검색어로 메일 삭제

Gmail 검색 문법을 그대로 사용할 수 있습니다.

```
Enter search keyword or Gmail query: subject:광고
```

| 입력 예시 | 설명 |
|-----------|------|
| `광고` | 제목·본문에 "광고" 포함 |
| `subject:뉴스레터` | 제목에 "뉴스레터" 포함 |
| `from:@naver.com` | 네이버에서 온 메일 |
| `older_than:2y` | 2년 이상 된 메일 |
| `has:attachment larger:10M` | 10MB 이상 첨부파일 |
| `is:unread older_than:6m` | 6개월 이상 된 읽지 않은 메일 |

#### 3 - 오래된 메일 삭제

입력한 일수보다 오래된 메일을 모두 삭제합니다.

```
Delete emails older than how many days? [365]: 180
```

#### 4 - 프로모션 메일 전체 삭제

Gmail이 자동으로 분류한 **프로모션** 탭의 메일을 모두 삭제합니다.

#### 5 - 소셜 메일 전체 삭제

Gmail이 자동으로 분류한 **소셜** 탭(Facebook, Twitter 등 SNS 알림)의 메일을 모두 삭제합니다.

#### 6 - 읽은 메일 아카이브

받은편지함에서 이미 읽은 메일을 아카이브합니다.
삭제하지 않고 받은편지함에서만 제거되며, 검색으로 다시 찾을 수 있습니다.

#### 7 - 받은편지함 통계 확인

카테고리별 메일 개수를 한눈에 확인합니다.

```
┌──────────────────────┬───────┐
│ Category             │ Count │
├──────────────────────┼───────┤
│ Total inbox          │  3842 │
│ Unread               │   127 │
│ Promotions           │  1205 │
│ Older than 1 year    │  2100 │
└──────────────────────┴───────┘
```

#### 8 - 상위 발신자 분석

받은편지함 최근 1000개 메일을 분석해 가장 많이 메일을 보낸 발신자 TOP 20을 보여줍니다.
어느 발신자를 차단할지 파악하는 데 유용합니다.

---

## 프로젝트 구조

```
ai-lab-gmail-cleaner/
├── gmail_cleaner.py    # 메인 CLI 스크립트 (메뉴 및 기능 구현)
├── auth.py             # Google OAuth2 인증 모듈
├── requirements.txt    # Python 의존성 패키지 목록
├── .gitignore          # credentials.json, token.json 등 민감 파일 제외
├── credentials.json    # (직접 추가) Google API 인증 키 - git 제외 파일
├── token.json          # (자동 생성) 인증 토큰 - git 제외 파일
└── README.md
```

---

## 문제 해결

### `credentials.json not found` 오류

`credentials.json` 파일이 프로젝트 폴더에 없는 경우입니다.
2단계 ⑤를 참고해 파일을 다운로드하고 프로젝트 폴더에 복사하세요.

### `pip`을 찾을 수 없다는 오류

Python 설치 시 PATH 설정이 안 된 경우입니다.
Python을 재설치하고 **"Add Python to PATH"** 를 체크하세요.
또는 `python -m pip install -r requirements.txt` 로 실행하세요.

### 브라우저 인증 후 `"액세스 차단됨"` 오류

OAuth 동의 화면의 테스트 사용자에 본인 계정이 추가되지 않은 경우입니다.
2단계 ④를 참고해 테스트 사용자를 추가하세요.

### 대량 삭제 시 오류 발생

Gmail API에는 사용량 제한(Quota)이 있습니다.
오류 발생 시 잠시 기다렸다가 다시 실행하세요. 도구가 자동으로 배치 처리합니다.

---

## 주의사항

- 삭제된 메일은 Gmail 휴지통으로 이동하며, 30일 후 영구 삭제됩니다.
- 처음 사용 시 반드시 `--dry-run` 모드로 테스트하세요.
- `credentials.json`, `token.json` 파일을 외부에 공유하거나 git에 커밋하지 마세요.
