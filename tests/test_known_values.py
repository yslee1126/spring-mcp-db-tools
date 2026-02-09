#!/usr/bin/env python3
"""
Test with known Java encrypted value
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp_spring_db_tools.common.jasypt_decryptor import JasyptDecryptor


def test_known_values():
    """Test with values we know from Java."""
    
    password = "your-password"
    algorithm = "PBEWithMD5AndDES"
    fixed_salt = "your-fixed-salt"
    
    print("=" * 80)
    print("Java와 동일한 값으로 테스트")
    print("=" * 80)
    print(f"Password: {password}")
    print(f"Algorithm: {algorithm}")
    print(f"Fixed Salt: {fixed_salt}")
    print()
    
    decryptor = JasyptDecryptor(password, algorithm=algorithm, fixed_salt=fixed_salt)
    
    # Java에서 확인된 값들
    test_cases = [
        ("dummy-enc-1", "expected-1"),
        ("dummy-enc-2", "expected-2"),
    ]
    
    for encrypted, expected in test_cases:
        try:
            decrypted = decryptor.decrypt(encrypted)
            status = "✅" if decrypted == expected or expected.startswith("unknown") else "❌"
            print(f"{status} ENC({encrypted})")
            print(f"   기대값: {expected}")
            print(f"   실제값: '{decrypted}'")
            print()
        except Exception as e:
            print(f"❌ ENC({encrypted})")
            print(f"   기대값: {expected}")
            print(f"   에러: {e}")
            print()


if __name__ == "__main__":
    test_known_values()
