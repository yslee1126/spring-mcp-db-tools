"""
Jasypt PBEWithMD5AndDES decryption module.
Supports decrypting values encrypted with Jasypt's standard encryption.
"""

import base64
import hashlib
import warnings
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# Suppress TripleDES deprecation warnings (Jasypt still uses it)
warnings.filterwarnings('ignore', category=DeprecationWarning, module='cryptography')


class JasyptDecryptor:
    """
    Decrypts values encrypted with Jasypt PBEWithMD5AndDES algorithm.
    
    This is compatible with Spring Boot's jasypt-spring-boot-starter using
    the default PBEWithMD5AndDES algorithm.
    """
    
    def __init__(self, password: str, iterations: int = 1000):
        """
        Initialize the decryptor with the encryption password.
        
        Args:
            password: The JASYPT_KEY used for encryption/decryption
            iterations: Number of iterations for key derivation (default: 1000)
        """
        self.password = password
        self.iterations = iterations
    
    def _derive_key_and_iv(self, salt: bytes) -> tuple[bytes, bytes]:
        """
        Derive the key and IV from password and salt using MD5.
        
        Args:
            salt: 8-byte salt extracted from the encrypted value
            
        Returns:
            Tuple of (key, iv) for DES decryption
        """
        # PBEWithMD5AndDES key derivation
        password_bytes = self.password.encode('utf-8')
        
        # Initial hash: password + salt
        data = password_bytes + salt
        
        # Iterate MD5 hashing
        for _ in range(self.iterations):
            md5 = hashlib.md5()
            md5.update(data)
            data = md5.digest()
        
        # First 8 bytes are the key, next 8 bytes are the IV
        key = data[:8]
        iv = data[8:16]
        
        return key, iv
    
    def decrypt(self, encrypted_value: str) -> str:
        """
        Decrypt a Jasypt-encrypted value.
        
        Args:
            encrypted_value: The encrypted string (without ENC() wrapper)
            
        Returns:
            The decrypted plaintext string
            
        Raises:
            ValueError: If decryption fails
        """
        try:
            # Decode base64
            encrypted_bytes = base64.b64decode(encrypted_value)
            
            # First 8 bytes are the salt
            salt = encrypted_bytes[:8]
            ciphertext = encrypted_bytes[8:]
            
            # Derive key and IV
            key, iv = self._derive_key_and_iv(salt)
            
            # Decrypt using DES-CBC
            cipher = Cipher(
                algorithms.TripleDES(key + key + key),  # DES key expanded to 3DES
                modes.CBC(iv),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            
            # Actually, PBEWithMD5AndDES uses single DES
            cipher = Cipher(
                algorithms.TripleDES(key * 3),  # Expand 8-byte key to 24 bytes for TripleDES
                modes.CBC(iv),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            # Remove PKCS7 padding
            padding_length = padded_plaintext[-1]
            plaintext = padded_plaintext[:-padding_length]
            
            return plaintext.decode('utf-8')
            
        except Exception as e:
            raise ValueError(f"Failed to decrypt value: {e}")
    
    def decrypt_if_encrypted(self, value: str) -> str:
        """
        Decrypt a value if it's wrapped in ENC(), otherwise return as-is.
        
        Args:
            value: The value to potentially decrypt
            
        Returns:
            Decrypted value if encrypted, original value otherwise
        """
        if value and value.startswith("ENC(") and value.endswith(")"):
            encrypted_value = value[4:-1]  # Remove ENC() wrapper
            return self.decrypt(encrypted_value)
        return value
