#!/usr/bin/env python3
"""
Manual Jasypt decryption test with detailed debugging.
"""

import base64
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


def test_decrypt_step_by_step():
    """Step by step decryption test."""
    
    # Configuration
    password = "your-password"
    fixed_salt = "your-fixed-salt"
    iterations = 1000
    
    # Test encrypted value (username)
    encrypted_value = "dummy-encrypted-value"
    
    print("=" * 80)
    print("Jasypt PBEWithMD5AndDES 복호화 상세 테스트")
    print("=" * 80)
    print(f"Password: {password}")
    print(f"Fixed Salt: {fixed_salt}")
    print(f"Iterations: {iterations}")
    print(f"Encrypted (base64): {encrypted_value}")
    print()
    
    # Step 1: Decode base64
    print("Step 1: Base64 디코딩")
    encrypted_bytes = base64.b64decode(encrypted_value)
    print(f"  Encrypted bytes length: {len(encrypted_bytes)}")
    print(f"  Encrypted bytes (hex): {encrypted_bytes.hex()}")
    print()
    
    # Step 2: Prepare salt
    print("Step 2: Salt 준비")
    salt = fixed_salt.encode('utf-8')
    print(f"  Salt (str): {fixed_salt}")
    print(f"  Salt (bytes): {salt}")
    print(f"  Salt (hex): {salt.hex()}")
    print(f"  Salt length: {len(salt)}")
    print()
    
    # Step 3: Derive key and IV using MD5
    print("Step 3: MD5로 Key와 IV 생성")
    password_bytes = password.encode('utf-8')
    print(f"  Password bytes: {password_bytes}")
    print(f"  Password (hex): {password_bytes.hex()}")
    
    # Initial: password + salt
    data = password_bytes + salt
    print(f"  Initial data (password + salt): {data.hex()}")
    
    # Iterate MD5
    for i in range(iterations):
        md5 = hashlib.md5()
        md5.update(data)
        data = md5.digest()
        if i < 3 or i >= iterations - 3:  # Show first 3 and last 3 iterations
            print(f"  Iteration {i+1}: {data.hex()}")
    
    key = data[:8]
    iv = data[8:16]
    
    print(f"  Final key (8 bytes): {key.hex()}")
    print(f"  Final IV (8 bytes): {iv.hex()}")
    print()
    
    # Step 4: Decrypt using DES (via TripleDES)
    print("Step 4: DES-CBC 복호화")
    ciphertext = encrypted_bytes  # All bytes are ciphertext (FixedSalt mode)
    print(f"  Ciphertext length: {len(ciphertext)}")
    print(f"  Ciphertext (hex): {ciphertext.hex()}")
    
    # DES key needs to be 24 bytes for TripleDES (repeat 8-byte key 3 times)
    des_key = key * 3
    print(f"  TripleDES key (24 bytes): {des_key.hex()}")
    
    try:
        cipher = Cipher(
            algorithms.TripleDES(des_key),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        
        print(f"  Padded plaintext length: {len(padded_plaintext)}")
        print(f"  Padded plaintext (hex): {padded_plaintext.hex()}")
        print(f"  Padded plaintext (bytes): {padded_plaintext}")
        print()
        
        # Step 5: Remove PKCS7 padding
        print("Step 5: PKCS7 패딩 제거")
        if len(padded_plaintext) > 0:
            padding_length = padded_plaintext[-1]
            print(f"  마지막 바이트 (padding length): {padding_length}")
            
            if padding_length > 0 and padding_length <= len(padded_plaintext):
                plaintext = padded_plaintext[:-padding_length]
                print(f"  Plaintext (hex): {plaintext.hex()}")
                print(f"  Plaintext (bytes): {plaintext}")
                
                try:
                    plaintext_str = plaintext.decode('utf-8')
                    print(f"  ✅ Plaintext (string): '{plaintext_str}'")
                except Exception as e:
                    print(f"  ❌ UTF-8 디코딩 실패: {e}")
            else:
                print(f"  ❌ 잘못된 padding length: {padding_length}")
        else:
            print(f"  ❌ Padded plaintext가 비어있음")
            
    except Exception as e:
        print(f"  ❌ 복호화 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_decrypt_step_by_step()
