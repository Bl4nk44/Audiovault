"""
Encryption utilities for securing sensitive credentials.
Uses Fernet symmetric encryption with keys derived from settings.
"""

import base64
import logging
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

# Salt for key derivation - should be stored securely in production
_DEFAULT_SALT = b"audiovault_encryption_salt_v1"


class EncryptionService:
    """
    Service for encrypting and decrypting sensitive data.
    Uses Fernet symmetric encryption.
    """

    def __init__(self, secret_key: Optional[str] = None, salt: Optional[bytes] = None):
        """
        Initialize encryption service.

        Args:
            secret_key: Secret key for encryption, defaults to JWT_SECRET_KEY
            salt: Salt for key derivation, defaults to application salt
        """
        self._fernet: Optional[Fernet] = None
        self._secret_key = secret_key
        self._salt = salt or _DEFAULT_SALT

    def _get_fernet(self) -> Fernet:
        """Lazy initialization of Fernet cipher."""
        if self._fernet is None:
            secret_key = self._secret_key
            if not secret_key:
                from app.core.config import settings

                secret_key = settings.JWT_SECRET_KEY

            # Derive a proper 32-byte key using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=self._salt,
                iterations=100_000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
            self._fernet = Fernet(key)

        return self._fernet

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.

        Args:
            plaintext: String to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        if not plaintext:
            return ""

        try:
            fernet = self._get_fernet()
            encrypted = fernet.encrypt(plaintext.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError("Encryption failed") from e

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt an encrypted string.

        Args:
            ciphertext: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string
        """
        if not ciphertext:
            return ""

        try:
            fernet = self._get_fernet()
            decrypted = fernet.decrypt(ciphertext.encode())
            return decrypted.decode()
        except InvalidToken:
            logger.error("Decryption failed: invalid token or wrong key")
            raise ValueError("Decryption failed: invalid token")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Decryption failed") from e

    def is_encrypted(self, value: str) -> bool:
        """
        Check if a value appears to be encrypted (Fernet format).

        Returns:
            True if value looks like Fernet-encrypted data
        """
        if not value:
            return False

        # Fernet tokens are base64 and start with gAAAAA...
        try:
            decoded = base64.urlsafe_b64decode(value)
            # Fernet tokens are at least 57 bytes
            return len(decoded) >= 57
        except Exception:
            return False


# Singleton instance
encryption_service = EncryptionService()


def encrypt_value(value: str) -> str:
    """Convenience function to encrypt a value."""
    return encryption_service.encrypt(value)


def decrypt_value(value: str) -> str:
    """Convenience function to decrypt a value."""
    return encryption_service.decrypt(value)
