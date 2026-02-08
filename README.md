# MCP Spring DB Tools

Spring Boot 프로젝트의 데이터베이스 스키마 조회 및 쿼리 실행계획 분석을 위한 MCP(Model Context Protocol) 서버입니다.

## 🎯 주요 기능

### 1. 데이터베이스 스키마 조회 (`get_schema_info`)
- 테이블, 컬럼, 인덱스, Foreign Key 정보 조회
- 컬럼 타입, NULL 허용 여부, 기본값, 코멘트 확인

### 2. 쿼리 실행계획 분석 (`get_execution_plan`)
- SQL 쿼리의 실행계획 분석
- 인덱스 사용 여부 및 성능 최적화 참고
- SELECT, INSERT, UPDATE, DELETE 쿼리 지원
- 성능 최적화 가이드 제공 (스캔 방식, 인덱스, 조인, 쿼리 구문 개선 제안)

### 3. 데이터소스 목록 조회 (`list_datasources`)
- 설정된 모든 데이터소스 목록 확인
- 데이터베이스 타입, 호스트, 포트 정보 확인

## 📋 지원 데이터베이스

- ✅ MySQL / MariaDB
- ✅ PostgreSQL
- ✅ MSSQL
- ✅ SQLite

---

## 사용 방법

사용 목적에 따라 선택하세요:

### 방법 1: MCP 설치해서 사용 (권장)

**이런 경우 사용:**
- Spring Boot 개발 중 DB 스키마 조회가 필요한 경우
- 쿼리 실행계획 분석이 필요한 경우
- 단순히 이 MCP 기능을 사용하고 싶은 경우

#### 1️⃣ 설치 (선택 - uvx 사용 시 불필요)

**방법 A: uvx 사용 (가장 권장 - 설치 불필요)**
```bash
# 아무것도 설치하지 않아도 됩니다!
```

**방법 B: pip 설치**
```bash
pip install mcp-spring-db-tools
```

#### 2️⃣ IDE MCP 설정

**Cursor / VS Code 설정 파일 위치:**
```
~/Library/Application Support/Cursor/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json
~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json
```

**IntelliJ AI Assistant 설정 파일 위치:**
```
~/Library/Application Support/JetBrains/IntelliJIdea<버전>/mcp_settings.json
```

**방법 A: uvx 사용 (설치 없이)**
```json
{
  "mcpServers": {
    "spring-db-tools": {
      "command": "uvx",
      "args": [
        "mcp-spring-db-tools",
        "/path/to/your-spring-project/src/main/resources/application.yml",
        ""
      ]
    }
  }
}
```

**방법 B: pip 설치 후**
```json
{
  "mcpServers": {
    "spring-db-tools": {
      "command": "mcp-spring-db-tools",
      "args": [
        "/path/to/your-spring-project/src/main/resources/application.yml",
        ""
      ]
    }
  }
}
```

**Jasypt 사용 시:**
```json
{
  "mcpServers": {
    "spring-db-tools": {
      "command": "uvx",
      "args": [
        "mcp-spring-db-tools",
        "/path/to/your-spring-project/src/main/resources/application.yml",
        "your-jasypt-secret-key"
      ]
    }
  }
}
```

#### 3️⃣ IDE 재시작

- IDE를 완전히 종료 후 다시 시작
- AI Assistant에서 "데이터소스 목록을 알려줘" 같은 질문으로 테스트

---

### 🔧 방법 2: 로컬에서 개발하며 사용

#### 1️⃣ 소스 코드 받기

```bash
git clone <repository-url>
cd mcp-spring-db-tools
```

#### 2️⃣ 개발 환경 설정

```bash
# 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 개발 모드로 설치
pip install -e .

# 테스트까지 돌리려면
pip install -e ".[dev]"
```

#### 3️⃣ IDE MCP 설정

**⚠️ 주의: 절대 경로 사용 필요!**

```json
{
  "mcpServers": {
    "spring-db-tools": {
      "command": "/absolute/path/to/mcp-spring-db-tools/venv/bin/mcp-spring-db-tools",
      "args": [
        "/path/to/your-spring-project/src/main/resources/application.yml",
        ""
      ]
    }
  }
}
```

**경로 확인 방법:**
```bash
# 프로젝트 디렉토리에서
which mcp-spring-db-tools
# 출력된 절대 경로를 복사해서 사용
```

#### 4️⃣ 개발 및 테스트

```bash
# 코드 수정
vim mcp_spring_db_tools/server.py

# 테스트 실행
pytest tests/ -v

# 커버리지 확인
pytest tests/ --cov=mcp_spring_db_tools --cov-report=html
```

**자세한 테스트 방법:** [테스트 가이드](tests/LOCAL_TEST_GUIDE.md)

---

## 📁 지원하는 application.yml 형식

### 단일 데이터소스

```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/mydb
    username: admin
    password: secret
    driver-class-name: com.mysql.cj.jdbc.Driver
```

### 다중 데이터소스

```yaml
spring:
  datasource:
    primary:
      url: jdbc:mysql://localhost:3306/main_db
      username: admin
      password: admin123
    secondary:
      url: jdbc:postgresql://localhost:5432/logs_db
      username: postgres
      password: postgres
```

또는:

```yaml
datasources:
  orders:
    url: jdbc:mysql://localhost:3306/orders
    username: user
    password: pass
  inventory:
    url: jdbc:mysql://localhost:3306/inventory
    username: user
    password: pass
```

### 환경변수 지원

```yaml
spring:
  datasource:
    url: ${DATABASE_URL:jdbc:mysql://localhost:3306/mydb}
    username: ${DB_USER:admin}
    password: ${DB_PASSWORD}
```

### SQLite 설정

**파일 기반 SQLite:**
```yaml
spring:
  datasource:
    url: jdbc:sqlite:./data/myapp.db
    driver-class-name: org.sqlite.JDBC
```

또는 절대 경로:
```yaml
spring:
  datasource:
    url: jdbc:sqlite:/Users/username/projects/myapp/data/app.db
    driver-class-name: org.sqlite.JDBC
```

**💡 SQLite 특징:**
- ✅ jar 파일 불필요 (Python 기본 내장 `sqlite3` 모듈 사용)
- ✅ 파일 기반 DB로 별도 서버 실행 불필요
- ✅ 테스트 및 개발 환경에 최적
- ✅ 인덱스 정보 및 실행계획 분석 모두 지원
- ✅ **상대 경로 자동 해석**: `./build/app.db` 같은 상대 경로는 프로젝트 루트 기준으로 자동 해석됩니다

**⚙️ 경로 해석 방식:**
- `application.yml`이 `src/main/resources/application.yml`에 위치한 경우, 프로젝트 루트를 자동으로 찾아 상대 경로를 해석합니다
- 예: `jdbc:sqlite:./build/app.db` → `/project-root/build/app.db`로 변환

## 🔐 Jasypt 암호화 지원

application.yml에서 `ENC()` 형식으로 암호화된 값을 자동으로 복호화합니다.

```yaml
spring:
  datasource:
    username: ENC(X8eU2hK9mLpF3...)
    password: ENC(Y7dT1gJ8nKoE4...)
```

**MCP 설정에서 Jasypt 키 전달:**
```json
{
  "args": [
    "/path/to/application.yml",
    "your-jasypt-encryption-key"
  ]
}
```

---

## 📝 라이선스

MIT License
