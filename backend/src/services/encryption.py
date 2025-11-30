"""Token encryption service using Fernet (symmetric encryption).

Provides:
- Secure encryption/decryption of sensitive tokens
- Key derivation from config encryption key
- Base64 encoding for database storage
"""
from cryptography.fernet import Fernet
import base64
import hashlib

from src.config import settings


class EncryptionService:
    """Service for encrypting and decrypting sensitive data.

    Uses Fernet (symmetric encryption) with AES-128.
    """

    def __init__(self):
        """Initialize encryption service with key from config."""
        # Derive Fernet key from config encryption key
        # Fernet requires exactly 32 bytes, base64-encoded
        key_bytes = settings.encryption_key.encode('utf-8')

        # Use SHA256 to ensure we have exactly 32 bytes
        hashed = hashlib.sha256(key_bytes).digest()

        # Base64 encode for Fernet
        fernet_key = base64.urlsafe_b64encode(hashed)

        self.cipher = Fernet(fernet_key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext string.

        Args:
            plaintext: String to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        # Encode to bytes
        plaintext_bytes = plaintext.encode('utf-8')

        # Encrypt
        encrypted_bytes = self.cipher.encrypt(plaintext_bytes)

        # Return as base64 string for database storage
        return base64.b64encode(encrypted_bytes).decode('utf-8')

    def decrypt(self, encrypted: str) -> str:
        """Decrypt encrypted string.

        Args:
            encrypted: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string

        Raises:
            InvalidToken: If decryption fails (corrupted data or wrong key)
        """
        # Decode from base64
        encrypted_bytes = base64.b64decode(encrypted.encode('utf-8'))

        # Decrypt
        decrypted_bytes = self.cipher.decrypt(encrypted_bytes)

        # Return as string
        return decrypted_bytes.decode('utf-8')


# Global encryption service instance
encryption_service = EncryptionService()
