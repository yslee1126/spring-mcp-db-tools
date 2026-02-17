# MCP Spring DB Tools

Spring Boot 프로젝트의 데이터베이스 스키마 조회 및 쿼리 실행계획 분석을 위한 MCP(Model Context Protocol) 서버입니다.

이 MCP 서버는 **stdio 방식만** 지원합니다.

## 🎯 주요 기능

### 1. 데이터베이스 스키마 조회 (`get_schema_info`)
- 테이블, 컬럼, 인덱스, Foreign Key 정보 조회
- 컬럼 타입, NULL 허용 여부, 기본값, 코멘트 확인

### 2. 쿼리 실행계획 분석 (`get_execution_plan`)
- SQL 쿼리의 실행계획 분석
- 인덱스 사용 여부 및 성능 최적화 참고
- SELECT, INSERT, UPDATE, DELETE 쿼리 지원
- 성능 최적화 가이드 제공 (스캔 방식, 인덱스, 조인, 쿼리 구문 개선 제안)

### 3. 저장 프로시저 및 뷰 조회 (`get_procedures`, `get_views`)
- 저장 프로시저(Stored Procedure) 목록 및 정의(SQL) 조회
- 뷰(View) 목록 및 정의(SQL) 조회
- 각 객체별 코멘트 및 상세 정보 확인

### 4. 데이터소스 목록 조회 (`list_datasources`)
- 설정된 모든 데이터소스 목록 확인
- 데이터베이스 타입, 호스트, 포트 정보 확인

## 📋 지원 데이터베이스

- ✅ MySQL / MariaDB
- ✅ PostgreSQL
- ✅ MSSQL
- ✅ SQLite

---

## 사용 방법

IDE의 MCP 설정 파일에 다음과 같이 추가하여 사용합니다. `uvx`를 사용하므로 별도의 설치 과정이 필요 없으며, 실행 시점에 필요한 패키지를 자동으로 로드합니다.

### IDE MCP 설정

**설정 파일 위치:**
- **Cursor / VS Code:** `~/Library/Application Support/Cursor(혹은 Code)/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- **IntelliJ AI Assistant:** `~/Library/Application Support/JetBrains/IntelliJIdea<버전>/mcp_settings.json`

**설정 예시 (JSON):**

```json
{
  "mcpServers": {
    "spring-db-tools": {
      "command": "uvx",
      "args": [
        "mcp-spring-db-tools",
        "/path/to/your-spring-project/src/main/resources/application.yml",
        "your-jasypt-secret-key",
        "PBEWithMD5AndDES",
        "your-fixed-salt"
      ],
      "env": {
        "DB_PASSWORD": "your_db_password_if_needed",
        "ANY_ENV_VAR": "value"
      }
    }
  }
}
```

**인자 설명:**
- `args[0]`: `application.yml` (또는 `.properties`) 파일의 **절대 경로** (필수)
- `args[1]`: Jasypt 암호화 키 (선택, 기본값: `""`)
- `args[2]`: Jasypt 알고리즘 (선택, 기본값: `PBEWithMD5AndDES`)
- `args[3]`: Jasypt Fixed Salt (선택, StringFixedSaltGenerator 사용 시 필요)

**환경 변수 (`env`):**
- Spring Boot 설정(`application.yml`)에서 `${DB_PASSWORD}`와 같이 환경 변수를 사용하는 경우, `env` 섹션에 해당 값을 정의할 수 있습니다.

### IDE 재시작

설정 후 IDE를 재시작하거나 MCP 서버 목록을 새로 고침하여 활성화합니다.

---


## 📁 파싱 가능한 applicaion.yml, application.properties 파일 형식

### 1. 단일 데이터소스

```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/mydb
    username: admin
    password: secret
    driver-class-name: com.mysql.cj.jdbc.Driver
```

### 2. 다중 데이터소스

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

### 3. 유연한 데이터소스 구조 (Custom Datasource Structure)

Spring 설정 하위의 임의의 키에 `datasource`가 포함된 경우도 인식합니다.

```yaml
spring:
  primary-db:
    datasource:
      url: jdbc:sqlserver://...
      username: ...
  secondary-db:
    datasource:
      url: jdbc:sqlserver://...
      username: ...
```

### 4. Properties 파일 지원 (`application.properties`)

`.yml` 파일 뿐만 아니라 `.properties` 파일도 지원합니다.

**표준 Spring Boot 스타일:**
```properties
spring.datasource.url=jdbc:mysql://localhost:3306/mydb
spring.datasource.username=admin
spring.datasource.password=secret
spring.datasource.driver-class-name=com.mysql.cj.jdbc.Driver
```

**Legacy / Flat 스타일 (Prefix 없이):**
```properties
jdbcUrl=jdbc:sqlserver://localhost:1433;databaseName=my_database
driverClassName=com.microsoft.sqlserver.jdbc.SQLServerDriver
username=ENC(dummy-encrypted-username)
password=ENC(dummy-encrypted-password)
```

**유연한 키 이름 지원:**
- `jdbcUrl`, `jdbc-url`, `url` 모두 인식
- `driverClassName`, `driver-class-name`, `driver-class` 모두 인식
- `username`, `user` 모두 인식
- `camelCase` 및 `kebab-case` 혼용 지원


### 5. 환경변수 지원

```yaml
spring:
  datasource:
    url: ${DATABASE_URL:jdbc:mysql://localhost:3306/mydb}
    username: ${DB_USER:admin}
    password: ${DB_PASSWORD}
```

### 6. SQLite 인 경우 yaml 설정

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

## 🔐 Jasypt 암호화 지원

application.yml에서 `ENC()` 형식으로 암호화된 값을 자동으로 복호화합니다.

```yaml
spring:
  datasource:
    username: ENC(X8eU2hK9mLpF3...)
    password: ENC(Y7dT1gJ8nKoE4...)
```

설정 방법은 상단의 [IDE MCP 설정](#ide-mcp-설정) 섹션을 참고하세요.

### 지원되는 알고리즘

- `PBEWithMD5AndDES` (기본값)
- `PBEWithMD5AndTripleDES`
- `PBEWITHHMACSHA512ANDAES_256`

**참고:** Fixed Salt는 salt 문자열의 첫 8바이트만 사용됩니다.


---

## 🛠️ 로컬 개발 및 테스트

로컬 개발 환경 설정, 테스트 실행 방법, 그리고 개발 중인 내용을 직접 MCP로 연결하는 방법은 다음 문서를 참고하세요.

[로컬 개발 가이드](tests/LOCAL_DEV_GUIDE.md)

## 📝 라이선스

MIT License
```
