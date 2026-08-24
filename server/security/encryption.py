# soap-web-services/server/security/encryption.py
from Crypto.Cipher import DES3
from Crypto.Util.Padding import pad, unpad
import base64
import hashlib
from typing import Optional

# Assuming config.py is in the same directory (server/) or project_root is in sys.path
# This import style relies on how the application is launched and sys.path is configured.
# If server/ is the root for execution (e.g. python app.py from server/), this is fine.
from config import Config


class TripleDESHelper: # Renamed to avoid confusion if 'TripleDES' is also a class name elsewhere
    """
    Triple DES encryption implementation.
    Uses MD5 hash of the key_string to derive a 16-byte key for 2-key TripleDES.
    Mode: ECB, Padding: PKCS7.
    """

    @staticmethod
    def _get_derived_key(key_string: str) -> bytes:
        """
        Derives a valid 2-key 3DES key in K1 + K2 + K1 format (24 bytes).
        """
        if not key_string:
            raise ValueError("Key string for TripleDES cannot be empty.")
        
        md5_digest = hashlib.md5(key_string.encode('utf-8')).digest()  # 16 bytes
        k1 = md5_digest[:8]
        k2 = md5_digest[8:]
        return k1 + k2 + k1  # 24-byte key

    @staticmethod
    def encrypt(key_string: str, text_to_encrypt: str) -> str:
        """Encrypt text using Triple DES ECB mode with PKCS7 padding."""
        if not isinstance(text_to_encrypt, str):
            # Or handle appropriately, e.g. convert, but spec implies XML string input
            raise TypeError("Text to encrypt must be a string.")

        try:
            derived_key = TripleDESHelper._get_derived_key(key_string)
            key = key_string.encode('utf-8')  # 24 bytes expected
            cipher = DES3.new(key, DES3.MODE_ECB)
            key_string = bytes.fromhex(key.hex()).decode("utf-8")
            print(f"Encoded Key: {key.hex()}")
            print(f"Key String: {key_string}")
            # cipher = DES3.new(derived_key, DES3.MODE_ECB)

            plaintext_bytes = text_to_encrypt.encode('utf-8')
            print(plaintext_bytes)
            padded_plaintext = pad(plaintext_bytes, DES3.block_size, style='pkcs7')
            encrypted_bytes = cipher.encrypt(padded_plaintext)

            return base64.b64encode(encrypted_bytes).decode('utf-8')
        except Exception as e:
            # Consider logging the specific error here before re-raising
            # logger.error(f"Encryption failed: {str(e)}", exc_info=True)
            raise ValueError(f"Encryption failed: {str(e)}") from e

    @staticmethod
    def decrypt(key_string: str, encrypted_text_base64: str) -> str:
        """Decrypt text using Triple DES ECB mode with PKCS7 padding."""
        if not isinstance(encrypted_text_base64, str):
            raise TypeError("Encrypted text must be a base64 encoded string.")
        if not encrypted_text_base64: # Handle empty string if it can occur
             raise ValueError("Encrypted text to decrypt cannot be empty.")

        try:
            derived_key = TripleDESHelper._get_derived_key(key_string)
            key = key_string.encode('utf-8')
            cipher = DES3.new(key, DES3.MODE_ECB)

            encrypted_bytes = base64.b64decode(encrypted_text_base64)
            decrypted_padded_bytes = cipher.decrypt(encrypted_bytes)

            original_plaintext_bytes = unpad(decrypted_padded_bytes, DES3.block_size, style='pkcs7')
            return original_plaintext_bytes.decode('utf-8')
        except (ValueError, TypeError) as e: # Specific to base64 or padding issues
             # logger.warning(f"Decryption failed due to padding or Base64 error: {str(e)}", exc_info=True)
             raise ValueError(f"Decryption failed (padding/Base64): {str(e)}") from e
        except Exception as e:
            # logger.error(f"Decryption failed: {str(e)}", exc_info=True)
            raise ValueError(f"Decryption failed: {str(e)}") from e


class DataSecurity:
    """Main security handler for XML data encryption/decryption using TripleDESHelper."""

    def __init__(self, secret_key_override: Optional[str] = None):
        self.secret_key = secret_key_override if secret_key_override is not None else Config.SECRET_KEY
        if not self.secret_key or self.secret_key == '!!!MISSING_SECRET_KEY_IN_ENV!!!':
            # This check is important because Config might have the placeholder
            raise ValueError("A valid secret key must be configured or provided for DataSecurity.")

    def encrypt_xml(self, xml_data: str) -> str:
        """Encrypt XML data."""
        # Allowing encryption of an empty string if that's a valid scenario,
        # otherwise, add: if not xml_data: raise ValueError("XML data cannot be empty")
        return TripleDESHelper.encrypt(self.secret_key, xml_data)

    def decrypt_xml(self, encrypted_xml: str) -> str:
        """Decrypt XML data."""
        if not encrypted_xml:
            raise ValueError("Encrypted XML to decrypt cannot be empty.")
        return TripleDESHelper.decrypt(self.secret_key, encrypted_xml)

__all__ = ['DataSecurity', 'TripleDESHelper']