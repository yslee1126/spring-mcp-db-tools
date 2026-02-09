"""
Jasypt decryption module.
Supports multiple Jasypt encryption algorithms and salt generators.
"""

import base64
import hashlib
import hmac
import warnings
from typing import Optional
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Suppress TripleDES deprecation warnings (Jasypt still uses it)
warnings.filterwarnings('ignore', category=DeprecationWarning, module='cryptography')


class JasyptDecryptor:
    """
    Decrypts values encrypted with Jasypt algorithms.
    
    Supports:
    - PBEWithMD5AndDES (default, legacy)
    - PBEWithMD5AndTripleDES
    - PBEWITHHMACSHA512ANDAES_256 (recommended)
    
    Supports both RandomSaltGenerator and StringFixedSaltGenerator.
    """
    
    def __init__(
        self,
        password: str,
        algorithm: str = "PBEWithMD5AndDES",
        iterations: int = 1000,
        fixed_salt: Optional[str] = None
    ):
        """
        Initialize the decryptor.
        
        Args:
            password: The JASYPT_KEY used for encryption/decryption
            algorithm: Encryption algorithm (default: PBEWithMD5AndDES)
            iterations: Number of iterations for key derivation (default: 1000)
            fixed_salt: Optional fixed salt string (for StringFixedSaltGenerator)
                       If None, assumes RandomSaltGenerator (salt in encrypted data)
        """
        self.password = password
        self.algorithm = algorithm.upper().replace("-", "")
        self.iterations = iterations
        # Jasypt's StringFixedSaltGenerator uses first 8 bytes of the salt string
        if fixed_salt:
            salt_bytes = fixed_salt.encode('utf-8')
            self.fixed_salt = salt_bytes[:8]  # Take only first 8 bytes
        else:
            self.fixed_salt = None
    
    def _derive_key_and_iv_md5(self, salt: bytes) -> tuple[bytes, bytes]:
        """
        Derive key and IV using MD5 (for PBEWithMD5And* algorithms).
        
        Args:
            salt: 8-byte salt
            
        Returns:
            Tuple of (key, iv)
        """
        password_bytes = self.password.encode('utf-8')
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
    
    def _derive_key_and_iv_hmac_sha512(self, salt: bytes) -> tuple[bytes, bytes]:
        """
        Derive key and IV using HMAC-SHA512 (for PBEWITHHMACSHA512ANDAES_256).
        
        Args:
            salt: Salt bytes
            
        Returns:
            Tuple of (key, iv)
        """
        password_bytes = self.password.encode('utf-8')
        
        # Use PBKDF2 with HMAC-SHA512
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA512(),
            length=32 + 16,  # 32 bytes for AES-256 key + 16 bytes for IV
            salt=salt,
            iterations=self.iterations,
            backend=default_backend()
        )
        derived = kdf.derive(password_bytes)
        
        # Split into key and IV
        key = derived[:32]  # 256 bits for AES-256
        iv = derived[32:48]  # 128 bits for IV
        
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
            
            # Extract salt and ciphertext
            if self.fixed_salt is not None:
                # Fixed salt mode: entire encrypted_bytes is ciphertext
                salt = self.fixed_salt
                ciphertext = encrypted_bytes
            else:
                # Random salt mode: first 8 bytes are salt
                salt = encrypted_bytes[:8]
                ciphertext = encrypted_bytes[8:]
            
            # Derive key and IV based on algorithm
            if self.algorithm in ["PBEWITHMD5ANDDES", "PBEWITHMD5ANDTRIPLEDES"]:
                key, iv = self._derive_key_and_iv_md5(salt)
            elif self.algorithm == "PBEWITHHMACSHA512ANDAES_256":
                key, iv = self._derive_key_and_iv_hmac_sha512(salt)
            else:
                raise ValueError(f"Unsupported algorithm: {self.algorithm}")
            
            # Decrypt based on algorithm
            if self.algorithm == "PBEWITHMD5ANDDES":
                # DES (single DES via TripleDES with repeated key)
                cipher = Cipher(
                    algorithms.TripleDES(key * 3),  # Expand 8-byte key to 24 bytes
                    modes.CBC(iv),
                    backend=default_backend()
                )
            elif self.algorithm == "PBEWITHMD5ANDTRIPLEDES":
                # Triple DES
                # Need 24-byte key for TripleDES
                if len(key) == 8:
                    key = key * 3
                cipher = Cipher(
                    algorithms.TripleDES(key[:24]),
                    modes.CBC(iv),
                    backend=default_backend()
                )
            elif self.algorithm == "PBEWITHHMACSHA512ANDAES_256":
                # AES-256
                cipher = Cipher(
                    algorithms.AES(key),
                    modes.CBC(iv[:16]),  # AES uses 16-byte IV
                    backend=default_backend()
                )
            
            decryptor = cipher.decryptor()
            padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            # Remove PKCS7 padding
            padding_length = padded_plaintext[-1]
            plaintext = padded_plaintext[:-padding_length]
            
            return plaintext.decode('utf-8')
            
        except Exception as e:
            raise ValueError(f"Failed to decrypt value with {self.algorithm}: {e}")
    
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
