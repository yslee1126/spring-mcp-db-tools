#!/usr/bin/env python3
"""
Test different salt processing methods to find the correct one.
"""

import base64
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


def derive_key_iv_md5(password: str, salt: bytes, iterations: int = 1000):
    """Derive key and IV using MD5."""
    password_bytes = password.encode('utf-8')
    data = password_bytes + salt
    
    for _ in range(iterations):
        md5 = hashlib.md5()
        md5.update(data)
        data = md5.digest()
    
    return data[:8], data[8:16]


def decrypt_with_salt(password: str, encrypted_base64: str, salt_bytes: bytes, iterations: int = 1000):
    """Decrypt with given salt bytes."""
    try:
        encrypted = base64.b64decode(encrypted_base64)
        key, iv = derive_key_iv_md5(password, salt_bytes, iterations)
        
        cipher = Cipher(
            algorithms.TripleDES(key * 3),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        padded = decryptor.update(encrypted) + decryptor.finalize()
        
        if len(padded) > 0:
            padding_len = padded[-1]
            if 0 < padding_len <= 8:  # Valid PKCS7 padding
                plaintext = padded[:-padding_len]
                try:
                    return plaintext.decode('utf-8')
                except:
                    return None
        return None
    except Exception as e:
        return None


def test_salt_variations():
    """Test different ways to process the salt string."""
    
    password = "your-password"
    salt_string = "your-salt-string"
    encrypted = "dummy-encrypted"  # Should decrypt to "test"
    expected = "test"
    
    print("=" * 80)
    print("다양한 Salt 처리 방식 테스트")
    print("=" * 80)
    print(f"Password: {password}")
    print(f"Salt String: {salt_string}")
    print(f"Encrypted: {encrypted}")
    print(f"Expected: {expected}")
    print()
    
    variations = []
    
    # 1. UTF-8 bytes directly (current implementation)
    salt_utf8 = salt_string.encode('utf-8')
    variations.append(("UTF-8 bytes as-is (10 bytes)", salt_utf8))
    
    # 2. First 8 bytes of UTF-8
    variations.append(("First 8 bytes of UTF-8", salt_utf8[:8]))
    
    # 3. Last 8 bytes of UTF-8
    variations.append(("Last 8 bytes of UTF-8", salt_utf8[-8:]))
    
    # 4. MD5 hash of salt string (first 8 bytes)
    salt_md5 = hashlib.md5(salt_utf8).digest()[:8]
    variations.append(("MD5 hash (first 8 bytes)", salt_md5))
    
    # 5. SHA1 hash of salt string (first 8 bytes)
    salt_sha1 = hashlib.sha1(salt_utf8).digest()[:8]
    variations.append(("SHA1 hash (first 8 bytes)", salt_sha1))
    
    # 6. Padded to 8 bytes with zeros
    salt_padded = (salt_utf8 + b'\x00' * 8)[:8]
    variations.append(("Padded with zeros to 8 bytes", salt_padded))
    
    # 7. XOR folded to 8 bytes
    if len(salt_utf8) > 8:
        salt_xor = bytearray(8)
        for i, b in enumerate(salt_utf8):
            salt_xor[i % 8] ^= b
        variations.append(("XOR folded to 8 bytes", bytes(salt_xor)))
    
    # 8. Repeated to fill 8 bytes
    salt_repeated = (salt_utf8 * ((8 // len(salt_utf8)) + 1))[:8]
    variations.append(("Repeated to 8 bytes", salt_repeated))
    
    # Test each variation
    for name, salt_bytes in variations:
        result = decrypt_with_salt(password, encrypted, salt_bytes)
        status = "✅" if result == expected else "❌"
        print(f"{status} {name}")
        print(f"   Salt (hex): {salt_bytes.hex()}")
        print(f"   Salt (len): {len(salt_bytes)}")
        print(f"   Result: '{result}'")
        print()
    
    # Also test the username encryption
    print("=" * 80)
    print("Username 값도 테스트")
    print("=" * 80)
    
    username_encrypted = "dummy-encrypted-username"
    username_expected = "USER_DUMMY"
    
    for name, salt_bytes in variations:
        result = decrypt_with_salt(password, username_encrypted, salt_bytes)
        status = "✅" if result == username_expected else "❌"
        if status == "✅":
            print(f"{status} {name}")
            print(f"   Salt (hex): {salt_bytes.hex()}")
            print(f"   Result: '{result}'")
            print()


if __name__ == "__main__":
    test_salt_variations()
