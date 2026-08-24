# soap-web-services/client/config.py
import os
import sys
from dotenv import load_dotenv

# Load .env file from the directory where config.py is located or client root.
# Adjust path if .env is elsewhere.
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if not os.path.exists(dotenv_path):
    # Attempt to load from parent directory if client/ is a subdirectory of the project root
    # You might prefer a more specific name like .env.client if it's in the root
    dotenv_path_alt = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(dotenv_path_alt):
        dotenv_path = dotenv_path_alt
    else: # If still not found, dotenv will just not load anything, which is fine if env vars are set globally
        print("DEBUG: client/.env or ../.env not found. Relying on globally set environment variables.", file=sys.stderr)

load_dotenv(dotenv_path=dotenv_path, override=True)


class Config:
    # Server Configuration (where the client connects to)
    SERVER_HOST: str = os.getenv('SOAP_SERVER_HOST', 'localhost')
    SERVER_PORT: int = int(os.getenv('SOAP_SERVER_PORT', '8000'))
    REQUEST_TIMEOUT: int = int(os.getenv('CLIENT_REQUEST_TIMEOUT', '30'))

    # SSL Configuration for client
    # CLIENT_SSL_VERIFY can be:
    # - "False" (string from .env) to disable verification.
    # - "/path/to/ca_bundle.pem" (string from .env) to specify a CA bundle or server cert.
    # - "True" (string from .env) to enable verification using default CAs.
    # - Not set (None), in which case SSL verification defaults to True (uses default CAs).
    _client_ssl_verify_env_str = os.getenv('CLIENT_SSL_VERIFY')
    CLIENT_SSL_VERIFY: str | bool

    if _client_ssl_verify_env_str is None:
        CLIENT_SSL_VERIFY = True # Default: verify with standard CAs if not set
        # print("DEBUG: CLIENT_SSL_VERIFY not in .env, defaulting to True (boolean)", file=sys.stderr)
    elif _client_ssl_verify_env_str.lower() == 'false':
        CLIENT_SSL_VERIFY = False
        # print("DEBUG: CLIENT_SSL_VERIFY from .env is 'false', set to False (boolean)", file=sys.stderr)
    elif _client_ssl_verify_env_str.lower() == 'true':
        CLIENT_SSL_VERIFY = True # Verify with standard CAs if explicitly 'true'
        # print("DEBUG: CLIENT_SSL_VERIFY from .env is 'true', set to True (boolean)", file=sys.stderr)
    else:
        # Assumed to be a path to a CA bundle or certificate
        CLIENT_SSL_VERIFY = _client_ssl_verify_env_str
        # print(f"DEBUG: CLIENT_SSL_VERIFY from .env is treated as a path: {CLIENT_SSL_VERIFY}", file=sys.stderr)

    CLIENT_SSL_CERT_PATH: str | None = os.getenv('CLIENT_SSL_CERT_PATH')
    CLIENT_SSL_KEY_PATH: str | None = os.getenv('CLIENT_SSL_KEY_PATH')

    # Security (matches server .env variables for shared secrets)
    SECRET_KEY: str = os.getenv('SECRET_KEY', '!!!MISSING_SECRET_KEY_IN_ENV!!!')
    SERVICE_USER: str = os.getenv('SERVICE_USER', '!!!MISSING_SERVICE_USER_IN_ENV!!!')
    SERVICE_PASSWORD: str = os.getenv('SERVICE_PASSWORD', '!!!MISSING_SERVICE_PASSWORD_IN_ENV!!!')

    # System mode (client's understanding of the server's mode for URL construction, etc.)
    SYSTEM_MODE: str = os.getenv('SYSTEM_MODE', 'TEST').upper()

    # Logging Configuration (client-side)
    LOG_LEVEL: str = os.getenv('CLIENT_LOG_LEVEL', 'INFO').upper()
    LOG_FORMAT: str = os.getenv(
        'CLIENT_LOG_FORMAT',
        '%(asctime)s - %(name)s - %(levelname)s - CLIENT - %(module)s:%(funcName)s:%(lineno)d - %(message)s'
    )
    LOG_FILE_PATH: str | None = os.getenv('CLIENT_LOG_FILE_PATH')


    @classmethod
    def get_wsdl_url(cls) -> str:
        """Generate the WSDL URL for the SOAP server."""
        protocol = 'https' # Default for TEST or if SSL isn't strictly configured client-side for verification
        host = cls.SERVER_HOST
        if host == '0.0.0.0': # Client should connect to localhost if server binds to 0.0.0.0
            host = 'localhost'

        # Determine protocol primarily based on SYSTEM_MODE (server's expected setup)
        if cls.SYSTEM_MODE == "LIVE": # LIVE should always attempt HTTPS
            protocol = 'https'
        elif cls.SYSTEM_MODE == "TEST":
            # For TEST mode, if CLIENT_SSL_VERIFY is a valid path to a cert,
            # it implies the client is prepared for HTTPS with that cert.
            # Otherwise, default to HTTP for TEST, as server might not have SSL.
            if isinstance(cls.CLIENT_SSL_VERIFY, str) and \
               cls.CLIENT_SSL_VERIFY.lower() not in ['true', 'false'] and \
               os.path.exists(cls.CLIENT_SSL_VERIFY):
                protocol = 'https'
            # If cls.CLIENT_SSL_VERIFY is a boolean (True/False from .env 'true'/'false'),
            # it governs verification behavior but doesn't force HTTPS for TEST.
            # The server app.py falls back to HTTP if its own SSL certs are missing.
            # So, 'http' is a sensible default for TEST unless client has specific cert for verification.

        return f"{protocol}://{host}:{cls.SERVER_PORT}/?wsdl"

    @classmethod
    def validate_critical_configs(cls):
        if cls.SECRET_KEY == '!!!MISSING_SECRET_KEY_IN_ENV!!!':
            print("CLIENT CRITICAL WARNING: SECRET_KEY is not set. Please set in .env", file=sys.stderr)
        if cls.SERVICE_USER == '!!!MISSING_SERVICE_USER_IN_ENV!!!':
            print("CLIENT CRITICAL WARNING: SERVICE_USER is not set. Please set in .env", file=sys.stderr)
        if cls.SERVICE_PASSWORD == '!!!MISSING_SERVICE_PASSWORD_IN_ENV!!!':
            print("CLIENT CRITICAL WARNING: SERVICE_PASSWORD is not set. Please set in .env", file=sys.stderr)

Config.validate_critical_configs()