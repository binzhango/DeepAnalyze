"""
Unit tests for the Credential Manager
Tests encryption, decryption, and security features
"""

import pytest
import os
import json
from cryptography.fernet import Fernet
from .credentials import CredentialManager, CredentialError


class TestCredentialManager:
    """Test suite for CredentialManager"""
    
    def test_init_with_provided_key(self):
        """Test initialization with a provided encryption key"""
        key = Fernet.generate_key().decode()
        manager = CredentialManager(encryption_key=key)
        assert manager is not None
        assert manager.validate_key()
    
    def test_init_with_env_variable(self):
        """Test initialization with encryption key from environment variable"""
        key = Fernet.generate_key().decode()
        os.environ['DATASOURCE_ENCRYPTION_KEY'] = key
        
        try:
            manager = CredentialManager()
            assert manager is not None
            assert manager.validate_key()
        finally:
            # Clean up
            if 'DATASOURCE_ENCRYPTION_KEY' in os.environ:
                del os.environ['DATASOURCE_ENCRYPTION_KEY']
    
    def test_init_with_auto_generated_key(self):
        """Test initialization with auto-generated key"""
        # Ensure no env variable is set
        if 'DATASOURCE_ENCRYPTION_KEY' in os.environ:
            del os.environ['DATASOURCE_ENCRYPTION_KEY']
        
        manager = CredentialManager()
        assert manager is not None
        assert manager.validate_key()
    
    def test_init_with_invalid_key(self):
        """Test initialization with invalid encryption key"""
        with pytest.raises(CredentialError):
            CredentialManager(encryption_key="invalid_key")
    
    def test_encrypt_credentials(self):
        """Test encrypting credentials"""
        manager = CredentialManager()
        credentials = {
            "username": "test_user",
            "password": "secret_password",
            "host": "localhost"
        }
        
        encrypted = manager.encrypt_credentials(credentials)
        
        # Encrypted string should be different from original
        assert encrypted != json.dumps(credentials)
        # Should be a string
        assert isinstance(encrypted, str)
        # Should not contain plaintext password
        assert "secret_password" not in encrypted
    
    def test_decrypt_credentials(self):
        """Test decrypting credentials"""
        manager = CredentialManager()
        original_credentials = {
            "username": "test_user",
            "password": "secret_password",
            "host": "localhost"
        }
        
        encrypted = manager.encrypt_credentials(original_credentials)
        decrypted = manager.decrypt_credentials(encrypted)
        
        assert decrypted == original_credentials
    
    def test_encrypt_decrypt_round_trip(self):
        """Test that encryption and decryption are inverse operations"""
        manager = CredentialManager()
        test_cases = [
            {"simple": "value"},
            {"username": "user", "password": "pass"},
            {"nested": {"key": "value"}},
            {"list": [1, 2, 3]},
            {"complex": {"a": 1, "b": [2, 3], "c": {"d": 4}}},
        ]
        
        for credentials in test_cases:
            encrypted = manager.encrypt_credentials(credentials)
            decrypted = manager.decrypt_credentials(encrypted)
            assert decrypted == credentials
    
    def test_decrypt_with_wrong_key(self):
        """Test that decryption fails with wrong key"""
        manager1 = CredentialManager()
        manager2 = CredentialManager()  # Different key
        
        credentials = {"password": "secret"}
        encrypted = manager1.encrypt_credentials(credentials)
        
        with pytest.raises(CredentialError):
            manager2.decrypt_credentials(encrypted)
    
    def test_decrypt_invalid_data(self):
        """Test that decryption fails with invalid encrypted data"""
        manager = CredentialManager()
        
        with pytest.raises(CredentialError):
            manager.decrypt_credentials("not_encrypted_data")
    
    def test_sanitize_config_default_keys(self):
        """Test sanitizing config with default sensitive keys"""
        manager = CredentialManager()
        config = {
            "username": "user",
            "password": "secret",
            "host": "localhost",
            "token": "abc123",
            "connection_string": "postgresql://user:pass@host/db"
        }
        
        sanitized = manager.sanitize_config(config)
        
        # Non-sensitive fields should remain
        assert sanitized["username"] == "user"
        assert sanitized["host"] == "localhost"
        
        # Sensitive fields should be redacted
        assert sanitized["password"] == "***REDACTED***"
        assert sanitized["token"] == "***REDACTED***"
        assert sanitized["connection_string"] == "***REDACTED***"
    
    def test_sanitize_config_custom_keys(self):
        """Test sanitizing config with custom sensitive keys"""
        manager = CredentialManager()
        config = {
            "username": "user",
            "custom_secret": "secret_value",
            "public_data": "visible"
        }
        
        sanitized = manager.sanitize_config(config, sensitive_keys=["custom_secret"])
        
        assert sanitized["username"] == "user"
        assert sanitized["public_data"] == "visible"
        assert sanitized["custom_secret"] == "***REDACTED***"
    
    def test_sanitize_config_does_not_modify_original(self):
        """Test that sanitize_config doesn't modify the original config"""
        manager = CredentialManager()
        config = {
            "password": "secret",
            "username": "user"
        }
        original_password = config["password"]
        
        sanitized = manager.sanitize_config(config)
        
        # Original should be unchanged
        assert config["password"] == original_password
        # Sanitized should be redacted
        assert sanitized["password"] == "***REDACTED***"
    
    def test_generate_key(self):
        """Test generating a new encryption key"""
        key = CredentialManager.generate_key()
        
        # Should be a string
        assert isinstance(key, str)
        # Should be valid for creating a manager
        manager = CredentialManager(encryption_key=key)
        assert manager.validate_key()
    
    def test_validate_key_success(self):
        """Test key validation with valid key"""
        manager = CredentialManager()
        assert manager.validate_key() is True
    
    def test_empty_credentials(self):
        """Test encrypting and decrypting empty credentials"""
        manager = CredentialManager()
        empty_creds = {}
        
        encrypted = manager.encrypt_credentials(empty_creds)
        decrypted = manager.decrypt_credentials(encrypted)
        
        assert decrypted == empty_creds
    
    def test_special_characters_in_credentials(self):
        """Test handling special characters in credentials"""
        manager = CredentialManager()
        credentials = {
            "password": "p@$$w0rd!#%&*()[]{}",
            "connection_string": "postgresql://user:p@ss@host:5432/db?ssl=true"
        }
        
        encrypted = manager.encrypt_credentials(credentials)
        decrypted = manager.decrypt_credentials(encrypted)
        
        assert decrypted == credentials
    
    def test_unicode_in_credentials(self):
        """Test handling unicode characters in credentials"""
        manager = CredentialManager()
        credentials = {
            "username": "用户",
            "password": "密码123",
            "note": "Ñoño 🔐"
        }
        
        encrypted = manager.encrypt_credentials(credentials)
        decrypted = manager.decrypt_credentials(encrypted)
        
        assert decrypted == credentials
    
    def test_large_credentials(self):
        """Test handling large credential dictionaries"""
        manager = CredentialManager()
        credentials = {
            f"key_{i}": f"value_{i}" * 100
            for i in range(100)
        }
        
        encrypted = manager.encrypt_credentials(credentials)
        decrypted = manager.decrypt_credentials(encrypted)
        
        assert decrypted == credentials
    
    def test_credentials_not_logged(self, caplog):
        """Test that credentials are never logged in plaintext"""
        manager = CredentialManager()
        credentials = {
            "password": "super_secret_password_12345",
            "token": "secret_token_67890"
        }
        
        # Perform operations
        encrypted = manager.encrypt_credentials(credentials)
        decrypted = manager.decrypt_credentials(encrypted)
        
        # Check that sensitive values don't appear in logs
        log_output = caplog.text
        assert "super_secret_password_12345" not in log_output
        assert "secret_token_67890" not in log_output
