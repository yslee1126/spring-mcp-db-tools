#!/usr/bin/env python3
"""
Debug script to test application.yml parsing and database connection.
"""

import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print(f"Python path: {sys.path[0]}", file=sys.stderr)
print(f"Script location: {__file__}", file=sys.stderr)


def test_decryption(jasypt_key: str = "", jasypt_algorithm: str = "PBEWithMD5AndDES", jasypt_salt: str = ""):
    """Test Jasypt decryption separately."""
    
    print("=" * 80)
    print("1. Jasypt 복호화 테스트")
    print("=" * 80)
    
    if not jasypt_key:
        print("⚠️  Jasypt 키가 제공되지 않았습니다.\n")
        return
    
    print(f"알고리즘: {jasypt_algorithm}")
    print(f"Salt 모드: {'FixedSalt' if jasypt_salt else 'RandomSalt'}")
    if jasypt_salt:
        print(f"Salt 값: {jasypt_salt}")
    print()
    
    try:
        from mcp_spring_db_tools.utils.jasypt_decryptor import JasyptDecryptor
        
        # 테스트할 암호화된 값들
        test_values = [
            "ENC(dummy-value-1)",
            "ENC(dummy-value-2)",
        ]
        
        decryptor = JasyptDecryptor(jasypt_key, algorithm=jasypt_algorithm, fixed_salt=jasypt_salt)
        
        for i, enc_value in enumerate(test_values, 1):
            try:
                decrypted = decryptor.decrypt_if_encrypted(enc_value)
                print(f"  값 #{i}: {enc_value}")
                print(f"    ✅ 복호화 성공: {decrypted}")
            except Exception as e:
                print(f"  값 #{i}: {enc_value}")
                print(f"    ❌ 복호화 실패: {e}")
        
        print()
        
    except Exception as e:
        print(f"❌ Jasypt 모듈 로드 실패: {e}")
        import traceback
        traceback.print_exc()


def test_parsing(yaml_path: str, jasypt_key: str = "", jasypt_algorithm: str = "PBEWithMD5AndDES", jasypt_salt: str = ""):
    """Test parsing application.yml and show what was found."""
    
    print("=" * 80)
    print("2. YAML 파싱 테스트")
    print("=" * 80)
    print(f"YAML 파일: {yaml_path}")
    print(f"Jasypt Key: {'(제공됨)' if jasypt_key else '(없음)'}")
    print()
    
    try:
        from mcp_spring_db_tools.utils.yaml_parser import ApplicationYamlParser
        
        parser = ApplicationYamlParser(yaml_path, jasypt_key, jasypt_algorithm, jasypt_salt)
        datasources = parser.parse()
        
        print(f"✅ 파싱 성공! {len(datasources)}개의 데이터소스를 찾았습니다.\n")
        
        for i, ds in enumerate(datasources, 1):
            print(f"데이터소스 #{i}: {ds.name}")
            print("-" * 80)
            print(f"  DB 타입: {ds.db_type}")
            print(f"  드라이버: {ds.driver_class}")
            print(f"  URL: {ds.url}")
            print(f"  호스트: {ds.host}")
            print(f"  포트: {ds.port}")
            print(f"  데이터베이스: {ds.database}")
            print(f"  사용자명: {ds.username}")
            print(f"  비밀번호: {'*' * len(ds.password) if ds.password else '(없음)'}")
            print()
        
        return datasources
        
    except Exception as e:
        print(f"❌ 파싱 실패: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_connector_creation(datasources):
    """Test creating database connectors without actual connection."""
    
    print("=" * 80)
    print("3. 커넥터 생성 테스트 (연결 없이)")
    print("=" * 80)
    
    if not datasources:
        print("⚠️  테스트할 데이터소스가 없습니다.\n")
        return
    
    try:
        from mcp_spring_db_tools.utils.db_connector import create_connector
        
        for ds in datasources:
            print(f"\n데이터소스: {ds.name}")
            print("-" * 80)
            
            try:
                connector = create_connector(ds)
                print(f"  ✅ 커넥터 생성 성공: {type(connector).__name__}")
            except Exception as e:
                print(f"  ❌ 커넥터 생성 실패: {e}")
                import traceback
                traceback.print_exc()
        
        print()
        
    except Exception as e:
        print(f"❌ db_connector 모듈 로드 실패: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main function."""
    
    if len(sys.argv) < 2:
        print("사용법: python debug_config.py <application.yml 경로> [jasypt_key] [jasypt_algorithm] [jasypt_salt]")
        print()
        print("예시:")
        print('  python debug_config.py /path/to/application.yml')
        print('  python debug_config.py /path/to/application.yml "your-secret-key"')
        print('  python debug_config.py /path/to/application.yml "key" "PBEWithMD5AndDES" "salt"')
        sys.exit(1)
    
    yaml_path = sys.argv[1]
    jasypt_key = sys.argv[2] if len(sys.argv) > 2 else ""
    jasypt_algorithm = sys.argv[3] if len(sys.argv) > 3 else "PBEWithMD5AndDES"
    jasypt_salt = sys.argv[4] if len(sys.argv) > 4 else ""
    
    print("🔍 MCP Spring DB Tools - 설정 디버깅\n")
    
    # Run tests (without actual DB connection to avoid timeouts)
    test_decryption(jasypt_key, jasypt_algorithm, jasypt_salt)
    datasources = test_parsing(yaml_path, jasypt_key, jasypt_algorithm, jasypt_salt)
    test_connector_creation(datasources)
    
    print("=" * 80)
    print("✅ 테스트 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()

