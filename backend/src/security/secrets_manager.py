"""Secrets management utilities for sensitive data.

Features:
- Encryption/decryption of sensitive data
- API key rotation utilities
- Secure password hashing
- Token generation
"""
import secrets
import hashlib
import base64
import logging
from typing import Optional, Tuple
from datetime import datetime, timedelta

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from passlib.context import CryptContext

from src.config import settings


logger = logging.getLogger(__name__)


class SecretsManager:
    """Manager for encryption and secrets handling."""

    def __init__(self):
        """Initialize secrets manager with encryption key."""
        # Derive Fernet key from encryption key
        self.fernet = self._get_fernet_cipher()

        # Password hashing context (bcrypt)
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def _get_fernet_cipher(self) -> Fernet:
        """Get Fernet cipher from encryption key.

        Returns:
            Fernet cipher instance
        """
        # Ensure key is bytes
        key_bytes = settings.encryption_key.encode()

        # Derive 32-byte key using PBKDF2
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'marketprep_salt',  # In production, use secure random salt
            iterations=100000,
        )
        derived_key = base64.urlsafe_b64encode(kdf.derive(key_bytes))

        return Fernet(derived_key)

    def encrypt_string(self, plaintext: str) -> str:
        """Encrypt a string value.

        Args:
            plaintext: String to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        try:
            encrypted_bytes = self.fernet.encrypt(plaintext.encode())
            return base64.urlsafe_b64encode(encrypted_bytes).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt_string(self, ciphertext: str) -> str:
        """Decrypt an encrypted string.

        Args:
            ciphertext: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string
        """
        try:
            encrypted_bytes = base64.urlsafe_b64decode(ciphertext.encode())
            decrypted_bytes = self.fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt.

        Args:
            password: Plain password

        Returns:
            Hashed password
        """
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash.

        Args:
            plain_password: Plain password to verify
            hashed_password: Hashed password to compare against

        Returns:
            True if password matches, False otherwise
        """
        return self.pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def generate_api_key(prefix: str = "mp", length: int = 32) -> str:
        """Generate a secure random API key.

        Args:
            prefix: Prefix for the key (e.g., "mp" for MarketPrep)
            length: Length of random part (default 32 bytes = 64 hex chars)

        Returns:
            API key in format: prefix_randomhex

        Example:
            >>> SecretsManager.generate_api_key("mp", 16)
            'mp_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6'
        """
        random_bytes = secrets.token_bytes(length)
        random_hex = random_bytes.hex()
        return f"{prefix}_{random_hex}"

    @staticmethod
    def generate_secret_token(length: int = 32) -> str:
        """Generate a secure random token.

        Args:
            length: Number of bytes (default 32)

        Returns:
            URL-safe base64-encoded token
        """
        return secrets.token_urlsafe(length)

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Create a hash of an API key for storage.

        Args:
            api_key: API key to hash

        Returns:
            SHA256 hash of the API key
        """
        return hashlib.sha256(api_key.encode()).hexdigest()


class APIKeyRotation:
    """Utilities for API key rotation management."""

    # Rotation periods
    ROTATION_WARNING_DAYS = 7  # Warn when key expires in 7 days
    ROTATION_PERIOD_DAYS = 90  # Rotate every 90 days

    @staticmethod
    def should_rotate_key(created_at: datetime, rotation_days: int = 90) -> bool:
        """Check if an API key should be rotated.

        Args:
            created_at: When the key was created
            rotation_days: Number of days before rotation (default 90)

        Returns:
            True if key should be rotated, False otherwise
        """
        age = datetime.utcnow() - created_at
        return age.days >= rotation_days

    @staticmethod
    def get_rotation_warning(created_at: datetime, rotation_days: int = 90) -> Optional[str]:
        """Get rotation warning message if key is expiring soon.

        Args:
            created_at: When the key was created
            rotation_days: Number of days before rotation

        Returns:
            Warning message if key is expiring soon, None otherwise
        """
        age = datetime.utcnow() - created_at
        days_remaining = rotation_days - age.days

        if days_remaining <= 0:
            return "API key has expired and should be rotated immediately"
        elif days_remaining <= 7:
            return f"API key expires in {days_remaining} days"

        return None

    @staticmethod
    def generate_key_pair() -> Tuple[str, str, datetime]:
        """Generate a new API key pair (key and hash).

        Returns:
            Tuple of (api_key, api_key_hash, created_at)
        """
        api_key = SecretsManager.generate_api_key()
        api_key_hash = SecretsManager.hash_api_key(api_key)
        created_at = datetime.utcnow()

        return api_key, api_key_hash, created_at


class SecureDataHandler:
    """Handler for secure storage of sensitive vendor data."""

    def __init__(self):
        """Initialize secure data handler."""
        self.secrets_manager = SecretsManager()

    def encrypt_oauth_token(self, token: str) -> str:
        """Encrypt an OAuth token for storage.

        Args:
            token: OAuth access token

        Returns:
            Encrypted token
        """
        return self.secrets_manager.encrypt_string(token)

    def decrypt_oauth_token(self, encrypted_token: str) -> str:
        """Decrypt an OAuth token.

        Args:
            encrypted_token: Encrypted token from database

        Returns:
            Decrypted token
        """
        return self.secrets_manager.decrypt_string(encrypted_token)

    def encrypt_api_credentials(self, credentials: dict) -> dict:
        """Encrypt API credentials dictionary.

        Args:
            credentials: Dictionary of credential key-value pairs

        Returns:
            Dictionary with encrypted values
        """
        encrypted = {}
        for key, value in credentials.items():
            if isinstance(value, str) and value:
                encrypted[key] = self.secrets_manager.encrypt_string(value)
            else:
                encrypted[key] = value

        return encrypted

    def decrypt_api_credentials(self, encrypted_credentials: dict) -> dict:
        """Decrypt API credentials dictionary.

        Args:
            encrypted_credentials: Dictionary with encrypted values

        Returns:
            Dictionary with decrypted values
        """
        decrypted = {}
        for key, value in encrypted_credentials.items():
            if isinstance(value, str) and value:
                try:
                    decrypted[key] = self.secrets_manager.decrypt_string(value)
                except Exception:
                    # Value might not be encrypted
                    decrypted[key] = value
            else:
                decrypted[key] = value

        return decrypted


# Global instances
secrets_manager = SecretsManager()
secure_data_handler = SecureDataHandler()


# Convenience functions
def generate_api_key(prefix: str = "mp", length: int = 32) -> str:
    """Generate API key (convenience wrapper)."""
    return SecretsManager.generate_api_key(prefix, length)


def hash_api_key(api_key: str) -> str:
    """Hash API key (convenience wrapper)."""
    return SecretsManager.hash_api_key(api_key)


def encrypt_string(plaintext: str) -> str:
    """Encrypt string (convenience wrapper)."""
    return secrets_manager.encrypt_string(plaintext)


def decrypt_string(ciphertext: str) -> str:
    """Decrypt string (convenience wrapper)."""
    return secrets_manager.decrypt_string(ciphertext)
