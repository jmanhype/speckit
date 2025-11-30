"""Security module for MarketPrep.

Provides:
- Input validation and sanitization
- Secrets management and encryption
- Password hashing
- API key generation and rotation
"""
from .input_validation import (
    InputValidator,
    sanitize_html,
    validate_email,
    sanitize_filename,
)
from .secrets_manager import (
    SecretsManager,
    SecureDataHandler,
    APIKeyRotation,
    secrets_manager,
    secure_data_handler,
    generate_api_key,
    hash_api_key,
    encrypt_string,
    decrypt_string,
)


__all__ = [
    # Input validation
    'InputValidator',
    'sanitize_html',
    'validate_email',
    'sanitize_filename',
    # Secrets management
    'SecretsManager',
    'SecureDataHandler',
    'APIKeyRotation',
    'secrets_manager',
    'secure_data_handler',
    'generate_api_key',
    'hash_api_key',
    'encrypt_string',
    'decrypt_string',
]
