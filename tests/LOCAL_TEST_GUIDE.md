# 🧪 테스트 가이드

## 📋 사전 준비

```bash
cd <PROJECT_ROOT>

# 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate

# 개발 모드로 설치
pip install -e .
```

> **참고:** `<PROJECT_ROOT>`는 `mcp-spring-db-tools` 프로젝트의 루트 디렉토리입니다.

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

## ✅ 테스트 체크리스트

- [ ] 모든 테스트 통과 (`pytest tests/ -v`)
- [ ] 코드 커버리지 확인
- [ ] 새로운 기능 추가 시 테스트 코드 작성
