# 🛠️ 로컬 개발 가이드

## 📋 사전 준비

로컬에서 개발 및 테스트를 진행하려면 먼저 의존성을 설치해야 합니다.

```bash
git clone https://github.com/yongsunglee/mcp-spring-db-tools.git
cd mcp-spring-db-tools

# 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate

# 개발 모드로 설치 (수정 사항이 즉시 반영됨)
pip install -e ".[dev]"
```

---

## 📁 프로젝트 구조

이 프로젝트의 주요 디렉토리 및 파일 구성은 다음과 같습니다.

```text
mcp-spring-db-tools/
├── mcp_spring_db_tools/        # 메인 패키지
│   ├── server.py               # MCP 서버 핵심 로직 (FastMCP 기반)
│   ├── common/                 # 공용 유틸리티 및 파서
│   │   ├── db_connector.py     # DB 연결 및 쿼리 실행 (MySQL, PSQL, SQLite 등)
│   │   ├── yaml_parser.py      # application.yml 파싱 및 데이터소스 추출
│   │   └── jasypt_decryptor.py # Jasypt 암호화 데이터 복호화 로직
│   ├── tools/                  # MCP 도구(Tool) 구현체
│   │   ├── schema_tool.py      # 스키마 정보 조회 도구
│   │   └── execution_plan_tool.py # 실행계획 분석 도구
│   └── __main__.py             # uvx 실행 진입점
├── tests/                      # 단위 테스트 및 테스트용 설정 파일
├── pyproject.toml              # 프로젝트 프로젝트 설정 및 의존성
└── README.md                   # 메인 안내 문서
```

---

## 🚀 로컬에서 개발 중인 MCP 서버 연결하기

`uvx`를 통한 설치 버전이 아닌, 현재 로컬에서 수정 중인 코드를 IDE(Cursor, VS Code 등)에 연결하여 테스트하려면 다음과 같이 설정합니다.

### IDE MCP 설정

**설정 파일 위치:**
- **Cursor / VS Code:** `~/Library/Application Support/Cursor(혹은 Code)/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- **IntelliJ AI Assistant:** `~/Library/Application Support/JetBrains/IntelliJIdea<버전>/mcp_settings.json`

**설정 예시 (JSON):**

```json
{
  "mcpServers": {
    "spring-db-tools-local": {
      "command": "/Users/your-name/path/to/mcp-spring-db-tools/venv/bin/python",
      "args": [
        "-m",
        "mcp_spring_db_tools",
        "/path/to/your-spring-project/src/main/resources/application.yml"
      ],
      "env": {
        "PYTHONPATH": "/Users/your-name/path/to/mcp-spring-db-tools"
      }
    }
  }
}
```

**중요 설정 포인트:**
1. **`command`**: 로컬 가상환경(`venv`)의 Python 실행 파일 **절대 경로**를 지정합니다.
2. **`args`**: `-m mcp_spring_db_tools`를 사용하여 모듈 방식으로 실행하고, 뒤에 대상 Spring Boot 프로젝트의 `application.yml` 경로를 추가합니다.
3. **`env.PYTHONPATH` (선택 사항)**: 만약 `pip install -e .` 과정을 생략했거나, 특정 상황에서 소스 코드를 찾지 못할 경우에만 프로젝트 루트의 **절대 경로**를 입력합니다.

---

## 🧪 단위 테스트 실행

### 모든 테스트 실행

```bash
pytest tests/ -v
```

### 특정 테스트 파일만 실행

```bash
# YAML 파서 테스트
pytest tests/test_yaml_parser.py -v

# Tools 테스트
pytest tests/test_tools.py -v
```

### 커버리지 포함 테스트

```bash
pytest tests/ --cov=mcp_spring_db_tools --cov-report=html
```

커버리지 리포트: `htmlcov/index.html`

---

## 📝 테스트 파일 설명

- **`test_yaml_parser.py`** - `application.yml` 파싱 로직 테스트
- **`test_tools.py`** - MCP Tools 동작 테스트
- **`test_application.yml`** - 테스트용 설정 파일 (테스트에서 사용)

---

## ✅ 개발 체크리스트

- [ ] 가상환경에서 `pip install -e .` 설치 확인
- [ ] 신규 기능 추가 시 `tests/` 폴더에 테스트 코드 작성
- [ ] `pytest`를 통한 전체 테스트 통과 확인
- [ ] IDE MCP 설정을 통한 실시간 동작 확인
