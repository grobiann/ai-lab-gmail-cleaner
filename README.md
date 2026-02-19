# Gmail Auto Cleaner

Gmail 받은편지함을 **완전 자동으로** 정리하는 도구입니다.
사용자 입력 없이 자동 스캔 → 라벨 적용 → 아카이브 → 삭제(확인 후) 순서로 처리합니다.

---

## 동작 방식

```
python gmail_cleaner.py
```

실행하면 아래 4단계가 자동으로 진행됩니다.

```
Phase 1 / 분석      받은편지함 자동 스캔
  ✓  뉴스레터 / 구독 메일       234개  →  삭제 예정 (확인 필요)
  ✓  프로모션 메일            1,205개  →  삭제 예정 (확인 필요)
  ✓  소셜 / SNS 알림 메일        87개  →  삭제 예정 (확인 필요)
  ✓  발신 전용(noreply) 메일     312개  →  자동 아카이브
  ✓  1년 이상 된 메일          2,100개  →  자동 아카이브

Phase 2 / 라벨 적용   Gmail 라벨을 생성하고 적용합니다.
  ✓  AutoClean/Newsletter  →  234개 적용 완료
  ✓  AutoClean/Promotion   →  1,205개 적용 완료
  ...

Phase 3 / 자동 처리   안전한 작업을 자동으로 처리합니다 (아카이브).
  ✓  발신 전용(noreply) 메일  312개 아카이브 완료
  ✓  1년 이상 된 메일       2,100개 아카이브 완료

Phase 4 / 삭제 확인   삭제 작업입니다. 그룹별로 확인 후 처리합니다.

  그룹 1/3  뉴스레터 / 구독 메일  →  234개 삭제 예정

   발신자                       제목                    날짜
   newsletter@medium.com        Weekly digest           Mon, 10 Feb ...
   noreply@github.com           Unsubscribe summary     Sun, 9 Feb ...
   ... 외 229개

  234개를 삭제하시겠습니까? [y/N]
```

---

## 자동 분류 규칙

| 카테고리 | Gmail 검색 조건 | 처리 방식 | 라벨 |
|----------|----------------|-----------|------|
| 뉴스레터 / 구독 메일 | `unsubscribe in:inbox` | **삭제 (확인 필요)** | `AutoClean/Newsletter` |
| 프로모션 메일 | `category:promotions` | **삭제 (확인 필요)** | `AutoClean/Promotion` |
| 소셜 / SNS 알림 | `category:social` | **삭제 (확인 필요)** | `AutoClean/Social` |
| 발신 전용 메일 | `from:noreply OR from:no-reply` | 자동 아카이브 | `AutoClean/NoReply` |
| 1년 이상 된 메일 | `older_than:365d in:inbox` | 자동 아카이브 | `AutoClean/OldMail` |

> **삭제**는 Gmail 휴지통으로 이동 (30일 후 영구 삭제) / **아카이브**는 받은편지함에서만 제거

---

## 1단계 - 사전 준비

### Python 설치 확인

Python 3.10 이상이 필요합니다.

```powershell
python --version
```

설치되어 있지 않다면 [python.org](https://www.python.org/downloads/)에서 최신 버전을 다운로드합니다.
설치 시 반드시 **"Add Python to PATH"** 체크박스를 체크하세요.

---

## 2단계 - Google Cloud Console 설정

Gmail API를 사용하기 위해 Google에서 인증 키를 발급받아야 합니다.

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
3. **Gmail API** 카드 클릭 → **"사용 설정"** 버튼 클릭
4. "관리" 버튼이 표시되면 활성화 완료

### ④ OAuth 동의 화면 설정

1. 왼쪽 메뉴 → **"API 및 서비스"** → **"OAuth 동의 화면"** 클릭
2. User Type: **"외부(External)"** 선택 → **"만들기"** 클릭
3. 앱 정보 입력:
   - 앱 이름: `gmail-cleaner` (임의로 입력 가능)
   - 사용자 지원 이메일: 본인 Gmail 주소 선택
   - 개발자 연락처 이메일: 본인 Gmail 주소 입력
4. **"저장 후 계속"** 반복 클릭
5. 테스트 사용자 페이지에서 **"+ ADD USERS"** → 본인 Gmail 주소 추가

> 앱이 Google 검증을 받지 않은 상태(테스트 모드)이므로 테스트 사용자로 등록해야 합니다.

### ⑤ credentials.json 다운로드

1. 왼쪽 메뉴 → **"API 및 서비스"** → **"사용자 인증 정보"** 클릭
2. **"+ 사용자 인증 정보 만들기"** → **"OAuth 클라이언트 ID"** 선택
3. 애플리케이션 유형: **"데스크톱 앱"** → **"만들기"** 클릭
4. 생성 완료 팝업에서 **"JSON 다운로드"** 클릭
5. 파일 이름을 `credentials.json`으로 변경
6. 프로젝트 폴더(`ai-lab-gmail-cleaner/`)에 복사

> **주의:** `credentials.json`과 `token.json`은 절대 git에 커밋하지 마세요. `.gitignore`에 이미 설정되어 있습니다.

---

## 3단계 - 설치

```powershell
# 프로젝트 폴더로 이동
cd C:\Projects\ai-lab-gmail-cleaner

# 가상 환경 생성 (최초 1회)
python -m venv venv

# 가상 환경 활성화
venv\Scripts\activate
# 프롬프트 앞에 (venv) 가 표시되면 성공

# 의존성 설치
pip install -r requirements.txt
```

---

## 4단계 - 실행

### 처음 실행 시 Google 인증

```powershell
# 가상 환경 활성화
venv\Scripts\activate

# 실행
python gmail_cleaner.py
```

1. 브라우저가 자동으로 열리며 Google 로그인 화면이 표시됩니다.
2. **"앱이 확인되지 않았습니다"** 경고 → **"고급"** → **"gmail-cleaner(안전하지 않음)으로 이동"** 클릭
   - 개인 앱이므로 정상적인 경고입니다.
3. Gmail 권한 허용 → **"계속"** 클릭
4. `token.json` 파일이 자동 생성됩니다. 이후 실행부터는 자동 로그인됩니다.

### Dry Run 모드 (실제 변경 없이 미리보기)

처음 사용 시 반드시 dry-run으로 먼저 확인하세요.

```powershell
python gmail_cleaner.py --dry-run
```

Phase 1~4가 동일하게 진행되지만 실제 삭제·아카이브·라벨 작업은 실행되지 않습니다.

### 실제 실행

```powershell
python gmail_cleaner.py
```

---

## 5단계 - 실행 흐름 상세

### Phase 1: 스캔 및 분류

입력 없이 자동으로 5가지 카테고리를 스캔합니다.
각 카테고리별 메일 수와 처리 방식(삭제/아카이브)을 표시합니다.

### Phase 2: 라벨 적용

분류된 메일에 Gmail 라벨을 자동으로 적용합니다.
라벨이 없으면 자동 생성됩니다.

Gmail에서 라벨 목록을 확인하면 `AutoClean/` 하위에 분류된 라벨들을 볼 수 있습니다.

```
AutoClean/
  └── Newsletter
  └── Promotion
  └── Social
  └── NoReply
  └── OldMail
```

### Phase 3: 자동 아카이브

**확인 없이** 자동 처리되는 안전한 작업입니다.
- 발신 전용(noreply) 메일 → 아카이브
- 1년 이상 된 메일 → 아카이브

아카이브는 삭제가 아닙니다. 받은편지함에서 제거될 뿐이며, Gmail 검색으로 언제든 다시 찾을 수 있습니다.

### Phase 4: 삭제 확인

삭제 그룹마다 **샘플 5개를 미리보기**로 표시하고 확인을 요청합니다.

```
  그룹 1/3  뉴스레터 / 구독 메일  →  234개 삭제 예정

   발신자                       제목              날짜
   newsletter@example.com       Weekly Digest     Mon, 10 Feb ...
   ...

  234개를 삭제하시겠습니까? [y/N]
```

- `y` 입력: 해당 그룹 삭제 진행
- `N` 또는 Enter: 해당 그룹 건너뜀, 다음 그룹으로 이동

---

## 규칙 커스터마이징

`gmail_cleaner.py` 파일의 `AUTO_RULES` 목록을 수정해 원하는 규칙을 추가/변경할 수 있습니다.

```python
AUTO_RULES: list[AutoRule] = [
    AutoRule(
        name="Newsletter",
        description="뉴스레터 / 구독 메일",
        query="unsubscribe in:inbox",   # Gmail 검색 쿼리
        label="AutoClean/Newsletter",    # 적용할 라벨 (None이면 라벨 미적용)
        action="delete",                 # "delete" 또는 "archive"
        safe=False,                      # False = 삭제 확인 필요, True = 자동 처리
    ),
    # 새 규칙 추가 예시:
    AutoRule(
        name="Updates",
        description="업데이트 알림 메일",
        query="category:updates",
        label="AutoClean/Updates",
        action="archive",
        safe=True,
    ),
]
```

### Gmail 검색 쿼리 예시

| 쿼리 | 설명 |
|------|------|
| `unsubscribe in:inbox` | 수신거부 링크가 있는 메일 |
| `category:promotions` | 프로모션 탭 메일 |
| `category:social` | 소셜 탭 메일 |
| `category:updates` | 업데이트 탭 메일 |
| `older_than:365d` | 1년 이상 된 메일 |
| `older_than:180d` | 6개월 이상 된 메일 |
| `from:@linkedin.com` | LinkedIn 메일 |
| `has:attachment larger:10M` | 10MB 이상 첨부파일 |
| `is:unread older_than:30d` | 30일 이상 읽지 않은 메일 |

---

## 프로젝트 구조

```
ai-lab-gmail-cleaner/
├── gmail_cleaner.py    # 메인 스크립트 (자동 파이프라인)
├── auth.py             # Google OAuth2 인증 모듈
├── requirements.txt    # Python 의존성 패키지 목록
├── .gitignore          # credentials.json, token.json 등 민감 파일 제외
├── credentials.json    # (직접 추가) Google API 인증 키 - git 제외
├── token.json          # (자동 생성) 인증 토큰 - git 제외
└── README.md
```

---

## 문제 해결

### `credentials.json not found` 오류

2단계 ⑤를 참고해 파일을 다운로드하고 프로젝트 폴더에 복사하세요.

### `pip` 명령을 찾을 수 없다는 오류

```powershell
python -m pip install -r requirements.txt
```

### 브라우저 인증 후 `"액세스 차단됨"` 오류

2단계 ④에서 테스트 사용자에 본인 계정을 추가했는지 확인하세요.

### 대량 처리 중 API 오류 발생

Gmail API 사용량 제한(Quota)에 걸린 경우입니다. 잠시 대기 후 재실행하세요.
도구는 배치 단위(50개)로 처리하며 각 배치 사이에 자동으로 딜레이를 줍니다.

---

## 주의사항

- 삭제된 메일은 Gmail 휴지통으로 이동하며, 30일 후 영구 삭제됩니다.
- 처음 사용 시 반드시 `--dry-run` 모드로 먼저 테스트하세요.
- `credentials.json`, `token.json` 파일을 외부에 공유하거나 git에 커밋하지 마세요.
