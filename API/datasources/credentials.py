"""
Credential Manager for Data Sources
Provides secure encryption and decryption of sensitive credentials
"""

import os
import json
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
import logging

# Configure logging to never log credentials
logger = logging.getLogger(__name__)


class CredentialError(Exception):
    """Exception raised for credential management errors"""
    pass


class CredentialManager:
    """Manages encryption and decryption of data source credentials
    
    This class provides secure storage and retrieval of sensitive credentials
    using Fernet symmetric encryption. Credentials are encrypted at rest and
    only decrypted in memory when needed.
    
    The encryption key can be provided via:
    1. Environment variable: DATASOURCE_ENCRYPTION_KEY
    2. Direct initialization parameter
    3. Auto-generated (not recommended for production)
    
    Attributes:
        _cipher: Fernet cipher instance for encryption/decryption
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """Initialize the credential manager
        
        Args:
            encryption_key: Base64-encoded Fernet key. If None, will attempt to
                          load from DATASOURCE_ENCRYPTION_KEY environment variable.
                          If not found, will generate a new key (not recommended
                          for production as it won't persist across restarts).
        
        Raises:
            CredentialError: If the encryption key is invalid
        """
        if encryption_key is None:
            encryption_key = os.environ.get('DATASOURCE_ENCRYPTION_KEY')
        
        if encryption_key is None:
            logger.warning(
                "No encryption key provided. Generating a new key. "
                "This key will not persist across restarts. "
                "Set DATASOURCE_ENCRYPTION_KEY environment variable for production use."
            )
            encryption_key = Fernet.generate_key().decode()
        
        try:
            # Ensure key is bytes
            if isinstance(encryption_key, str):
                encryption_key = encryption_key.encode()
            
            self._cipher = Fernet(encryption_key)
            logger.info("Credential manager initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize credential manager")
            raise CredentialError(f"Invalid encryption key: {str(e)}") from e
    
    def encrypt_credentials(self, credentials: Dict[str, Any]) -> str:
        """Encrypt credentials dictionary to an encrypted string
        
        Args:
            credentials: Dictionary containing sensitive credential data
        
        Returns:
            Base64-encoded encrypted string
        
        Raises:
            CredentialError: If encryption fails
        """
        try:
            # Convert credentials to JSON string
            credentials_json = json.dumps(credentials)
            credentials_bytes = credentials_json.encode()
            
            # Encrypt
            encrypted_bytes = self._cipher.encrypt(credentials_bytes)
            encrypted_str = encrypted_bytes.decode()
            
            logger.info("Credentials encrypted successfully")
            return encrypted_str
        except Exception as e:
            logger.error("Failed to encrypt credentials")
            raise CredentialError(f"Encryption failed: {str(e)}") from e
    
    def decrypt_credentials(self, encrypted_credentials: str) -> Dict[str, Any]:
        """Decrypt encrypted credentials string to dictionary
        
        Args:
            encrypted_credentials: Base64-encoded encrypted string
        
        Returns:
            Dictionary containing decrypted credential data
        
        Raises:
            CredentialError: If decryption fails
        """
        try:
            # Ensure encrypted_credentials is bytes
            if isinstance(encrypted_credentials, str):
                encrypted_credentials = encrypted_credentials.encode()
            
            # Decrypt
            decrypted_bytes = self._cipher.decrypt(encrypted_credentials)
            decrypted_json = decrypted_bytes.decode()
            
            # Parse JSON
            credentials = json.loads(decrypted_json)
            
            logger.info("Credentials decrypted successfully")
            return credentials
        except Exception as e:
            logger.error("Failed to decrypt credentials")
            raise CredentialError(f"Decryption failed: {str(e)}") from e
    
    def sanitize_config(self, config: Dict[str, Any], sensitive_keys: Optional[list] = None) -> Dict[str, Any]:
        """Remove sensitive information from config for logging/display
        
        This method creates a copy of the config with sensitive fields masked.
        Useful for logging or returning config to clients without exposing secrets.
        
        Args:
            config: Configuration dictionary that may contain sensitive data
            sensitive_keys: List of keys to mask. If None, uses default list:
                          ['password', 'token', 'secret', 'key', 'connection_string',
                           'sas_token', 'api_key', 'access_key']
        
        Returns:
            Dictionary with sensitive values replaced by '***REDACTED***'
        """
        if sensitive_keys is None:
            sensitive_keys = [
                'password', 'token', 'secret', 'key', 'connection_string',
                'sas_token', 'api_key', 'access_key', 'credentials'
            ]
        
        sanitized = config.copy()
        
        for key in sensitive_keys:
            if key in sanitized:
                sanitized[key] = '***REDACTED***'
        
        return sanitized
    
    @staticmethod
    def generate_key() -> str:
        """Generate a new Fernet encryption key
        
        Returns:
            Base64-encoded encryption key as string
        """
        key = Fernet.generate_key()
        return key.decode()
    
    def validate_key(self) -> bool:
        """Validate that the encryption key is working
        
        Returns:
            True if key is valid and can encrypt/decrypt
        """
        try:
            test_data = {"test": "data"}
            encrypted = self.encrypt_credentials(test_data)
            decrypted = self.decrypt_credentials(encrypted)
            return decrypted == test_data
        except Exception:
            return False
