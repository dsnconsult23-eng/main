# soap-web-services/client/crypto_utils.py
from __future__ import annotations # VERY FIRST LINE

from Crypto.Cipher import DES3
from Crypto.Util.Padding import pad, unpad # For PKCS7 padding
import hashlib # For MD5
import base64

# This client-side crypto utility should be an exact mirror of the server-side one
# for generating keys, encrypting, and decrypting.

class TripleDESHelperClient: # Mirroring the server's helper class name
    """
    Triple DES encryption implementation for the client.
    Uses MD5 hash of the key_string to derive a 16-byte key for 2-key TripleDES.
    Mode: ECB, Padding: PKCS7.
    Matches server-side TripleDESHelper.
    """

    @staticmethod
    def _get_derived_key(key_string: str) -> bytes:
        """
        Derives a 16-byte key using MD5 hash of the input UTF-8 encoded string.
        """
        if not key_string:
            raise ValueError("Key string for TripleDES cannot be empty.")
        return hashlib.md5(key_string.encode('utf-8')).digest() # Returns 16 bytes

    @staticmethod
    def encrypt(key_string: str, text_to_encrypt: str) -> str:
        """Encrypt text using Triple DES ECB mode with PKCS7 padding."""
        if not isinstance(text_to_encrypt, str):
            raise TypeError("Text to encrypt must be a string.")
        try:
            derived_key = TripleDESHelperClient._get_derived_key(key_string)
            cipher = DES3.new(derived_key, DES3.MODE_ECB) # Key is 16 bytes

            plaintext_bytes = text_to_encrypt.encode('utf-8')
            padded_plaintext = pad(plaintext_bytes, DES3.block_size, style='pkcs7')
            encrypted_bytes = cipher.encrypt(padded_plaintext)

            return base64.b64encode(encrypted_bytes).decode('utf-8')
        except Exception as e:
            raise ValueError(f"Client Encryption failed: {str(e)}") from e

    @staticmethod
    def decrypt(key_string: str, encrypted_text_base64: str) -> str:
        """Decrypt text using Triple DES ECB mode with PKCS7 padding."""
        if not isinstance(encrypted_text_base64, str):
            raise TypeError("Encrypted text must be a base64 encoded string.")
        if not encrypted_text_base64:
            raise ValueError("Encrypted text to decrypt cannot be empty.")
        try:
            derived_key = TripleDESHelperClient._get_derived_key(key_string)
            cipher = DES3.new(derived_key, DES3.MODE_ECB)

            encrypted_bytes = base64.b64decode(encrypted_text_base64)
            decrypted_padded_bytes = cipher.decrypt(encrypted_bytes)

            original_plaintext_bytes = unpad(decrypted_padded_bytes, DES3.block_size, style='pkcs7')
            return original_plaintext_bytes.decode('utf-8')
        except (ValueError, TypeError) as e:
             raise ValueError(f"Client Decryption failed (padding/Base64): {str(e)}") from e
        except Exception as e:
            raise ValueError(f"Client Decryption failed: {str(e)}") from e

# For direct use if preferred over DataSecurityClient instantiation
def encrypt_3des_ecb_pkcs7(secret_key: str, plaintext_data: str) -> str:
    return TripleDESHelperClient.encrypt(secret_key, plaintext_data)

def decrypt_3des_ecb_pkcs7(secret_key: str, encrypted_base64_data: str) -> str:
    return TripleDESHelperClient.decrypt(secret_key, encrypted_base64_data)

# Optional: A DataSecurity like class for the client if complex key management is needed
# For now, direct use of encrypt/decrypt functions or TripleDESHelperClient static methods is fine.