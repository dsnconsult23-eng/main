# soap-web-services/server/config.py
import os
import sys
from dotenv import load_dotenv

# Load .env file from the directory where config.py is located or project root.
# Adjust path if .env is elsewhere.
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if not os.path.exists(dotenv_path):
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env') # Check project root
load_dotenv(dotenv_path=dotenv_path)

class Config:
    # Server Configuration
    SERVER_HOST: str = os.getenv('SERVER_HOST', '0.0.0.0')
    SERVER_PORT: int = int(os.getenv('SERVER_PORT', '8001'))
    REQUEST_TIMEOUT: int = int(os.getenv('REQUEST_TIMEOUT', '30'))
    # The encrypted SOAP XML is larger than the original documents because the
    # payload is base64 encoded before and after encryption. Spyne defaults to
    # only 2 MiB, which is too small even for a few megabytes of documents.
    MAX_REQUEST_SIZE_MB: int = int(os.getenv('MAX_REQUEST_SIZE_MB', '25'))

    # SSL Configuration
    # Paths should be absolute or relative to a known location.
    # Example: os.path.join(os.path.dirname(__file__), 'ssl', 'cert.pem')
    SSL_CERT_PATH: str | None = os.getenv('SSL_CERT_PATH')
    SSL_KEY_PATH: str | None = os.getenv('SSL_KEY_PATH')

    # Security
    SECRET_KEY: str = os.getenv('SECRET_KEY', '!!!MISSING_SECRET_KEY_IN_ENV!!!')
    SERVICE_USER: str = os.getenv('SERVICE_USER', '!!!MISSING_SERVICE_USER_IN_ENV!!!')
    SERVICE_PASSWORD: str = os.getenv('SERVICE_PASSWORD', '!!!MISSING_SERVICE_PASSWORD_IN_ENV!!!')

    # System mode
    SYSTEM_MODE: str = os.getenv('SYSTEM_MODE', 'TEST').upper()

    # Logging Configuration
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO').upper()
    LOG_FORMAT: str = os.getenv(
        'LOG_FORMAT',
        '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s'
    )
    LOG_FILE_PATH: str | None = os.getenv('LOG_FILE_PATH') # Example: server.log or /var/log/app/server.log

    # Database Configuration (for Informix via JayDeBeApi)
    DB_USER: str | None = os.getenv('DB_USER')
    DB_PASSWORD: str | None = os.getenv('DB_PASSWORD')
    DB_HOST: str | None = os.getenv('DB_HOST')
    DB_PORT: str | None = os.getenv('DB_PORT')
    DB_NAME: str | None = os.getenv('DB_NAME')
    DB_DRIVER_PATH_1: str | None = os.getenv('DB_DRIVER_PATH_1') # e.g., path to jdbc-4.50.4.1.jar
    DB_DRIVER_PATH_2: str | None = os.getenv('DB_DRIVER_PATH_2') # e.g., path to bson-4.2.0.jar
    JAVA_HOME: str | None = os.getenv('JAVA_HOME')

    # Document storage
    DOCUMENT_STORAGE_PATH: str = os.getenv(
        'DOCUMENT_STORAGE_PATH',
        os.path.join(os.path.dirname(__file__), 'storage', 'policy_documents')
    )
    DOCUMENTS_TABLE: str = os.getenv('DOCUMENTS_TABLE', 'appuser.polisa_sertifikati_doc')
    CLAIM_DOCUMENT_STORAGE_PATH: str = os.getenv(
        'CLAIM_DOCUMENT_STORAGE_PATH',
        os.path.join(os.path.dirname(__file__), 'storage', 'claim_documents')
    )
    CLAIM_DOCUMENTS_TABLE: str = os.getenv('CLAIM_DOCUMENTS_TABLE', 'appuser.claim_documents')


    @classmethod
    def get_wsdl_url(cls) -> str:
        """
        Generate the externally visible WSDL URL.

        PUBLIC_BASE_URL has priority (for reverse proxy setups).
        Fallback is local SERVER_HOST:SERVER_PORT.
        """
        public_base = os.getenv("PUBLIC_BASE_URL")
        if public_base:
            return f"{public_base}/?wsdl"

        # Fallback (local / dev mode)
        protocol = 'http'
        cert_exists = cls.SSL_CERT_PATH and os.path.exists(cls.SSL_CERT_PATH)
        key_exists = cls.SSL_KEY_PATH and os.path.exists(cls.SSL_KEY_PATH)

        if cert_exists and key_exists:
            protocol = 'https'

        host = cls.SERVER_HOST
        return f"{protocol}://{host}:{cls.SERVER_PORT}/?wsdl"

    # def get_wsdl_url(cls) -> str:
    #     """Generate the WSDL URL as a concrete string"""
    #     protocol = 'http'
    #     # Ensure paths are checked for existence if provided
    #     cert_exists = cls.SSL_CERT_PATH and os.path.exists(cls.SSL_CERT_PATH)
    #     key_exists = cls.SSL_KEY_PATH and os.path.exists(cls.SSL_KEY_PATH)

    #     if cert_exists and key_exists:
    #         protocol = 'https'
        
    #     host = cls.SERVER_HOST
    #     # Client-side connections should use localhost if server binds to 0.0.0.0
    #     # This WSDL URL is what the server itself reports, so 0.0.0.0 might be fine
    #     # or use a specific externally accessible hostname if different from SERVER_HOST.
    #     return f"{protocol}://{host}:{cls.SERVER_PORT}/?wsdl"

    @classmethod
    def validate_critical_configs(cls):
        """Validates that critical configurations are not using placeholder defaults."""
        if cls.SECRET_KEY == '!!!MISSING_SECRET_KEY_IN_ENV!!!':
            print("CRITICAL WARNING: SECRET_KEY is not set. Using insecure default. Please set in .env", file=sys.stderr)
        if cls.SERVICE_USER == '!!!MISSING_SERVICE_USER_IN_ENV!!!':
            print("CRITICAL WARNING: SERVICE_USER is not set. Using insecure default. Please set in .env", file=sys.stderr)
        if cls.SERVICE_PASSWORD == '!!!MISSING_SERVICE_PASSWORD_IN_ENV!!!':
            print("CRITICAL WARNING: SERVICE_PASSWORD is not set. Using insecure default. Please set in .env", file=sys.stderr)

# Perform validation when this module is loaded.
Config.validate_critical_configs()
