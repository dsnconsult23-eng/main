#!/usr/bin/env python3
import os
import sys
import ssl
import logging # Import logging
from spyne import Application
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
from wsgiref.simple_server import make_server

# Ensure project root is in path to find config and services
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

# This setup assumes 'services', 'security', 'models', 'storage', 'utils' are subdirectories of 'server' (where app.py is)
# or are directly in project_root and project_root is added to sys.path.
# Ensure Python can find your modules. Standard package structure is better.
# e.g. from server.config import Config if 'server' is a package.

from config import Config # Should now be found due to sys.path modification
from services.soap_service import InsuranceSoapService
from utils.logger import setup_logging # Import the logging setup function

# --- Call Logging Setup Early ---
# This will configure the root logger based on settings in Config
# All subsequent logging calls will use this configuration.
setup_logging()
logger = logging.getLogger(__name__) # Get a logger for this module
from typing import Optional

def create_soap_application() -> Application:
    """Create and configure SOAP application."""
    logger.info("Creating Spyne SOAP application.")
    application = Application(
        [InsuranceSoapService],
        tns='insurance.services',
        in_protocol=Soap11(validator='lxml'),
        out_protocol=Soap11()
    )
    logger.info("Spyne application created.")
    return application


# Gunicorn WSGI entrypoint
def create_wsgi_application() -> WsgiApplication:
    """Create the WSGI wrapper with the configured SOAP request limit."""
    max_content_length = Config.MAX_REQUEST_SIZE_MB * 1024 * 1024
    logger.info("SOAP maximum request size: %s MiB", Config.MAX_REQUEST_SIZE_MB)
    return WsgiApplication(
        create_soap_application(),
        max_content_length=max_content_length,
    )


application = create_wsgi_application()


def validate_ssl_files(cert_path: Optional[str], key_path: Optional[str]):
    """Validate SSL certificate and key files."""
    if not cert_path or not os.path.exists(cert_path):
        raise FileNotFoundError(f"SSL certificate not found or path not set: {cert_path}")
    if not key_path or not os.path.exists(key_path):
        raise FileNotFoundError(f"SSL key not found or path not set: {key_path}")
    
    logger.info(f"Validating SSL certificate: {cert_path} and key: {key_path}")
    # Basic check by trying to load them into a context
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert_path, key_path)
        logger.info("SSL certificate and key validated successfully.")
    except ssl.SSLError as e:
        logger.error(f"SSL certificate and key mismatch or error: {str(e)}", exc_info=True)
        raise ValueError(f"SSL certificate and key mismatch or error: {str(e)}") from e
    except Exception as e:
        logger.error(f"Unexpected error validating SSL files: {str(e)}", exc_info=True)
        raise ValueError(f"Unexpected error validating SSL files: {str(e)}") from e


def run_server():
    """Run the SOAP server with optional SSL."""
    try:
        # Config validation happens when config.py is imported.
        # Config.validate_critical_configs() # Or call it explicitly here
        
        wsgi_app = create_wsgi_application()
        
        # Use host and port from Config
        host = Config.SERVER_HOST
        port = Config.SERVER_PORT
        
        server = make_server(host, port, wsgi_app)
        
        protocol = 'http' # Default protocol
        
        # SSL Configuration from Config
        if Config.SSL_CERT_PATH and Config.SSL_KEY_PATH:
            logger.info("Attempting to configure SSL.")
            try:
                validate_ssl_files(Config.SSL_CERT_PATH, Config.SSL_KEY_PATH)
                
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                context.load_cert_chain(
                    certfile=Config.SSL_CERT_PATH,
                    keyfile=Config.SSL_KEY_PATH
                )
                
                # Security enhancements for SSL context (good practice)
                context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1 # Prefer TLS 1.2+
                # context.options |= ssl.OP_NO_SSLv2 # Usually default/deprecated in modern Python
                # context.options |= ssl.OP_NO_SSLv3 # Usually default/deprecated
                context.set_ciphers('ECDHE+AESGCM:CHACHA20') # Modern secure ciphers
                
                server.socket = context.wrap_socket(server.socket, server_side=True)
                protocol = 'https'
                logger.info(f"🔐 SSL enabled successfully using:")
                logger.info(f"    Certificate: {Config.SSL_CERT_PATH}")
                logger.info(f"    Private Key: {Config.SSL_KEY_PATH}")
            except (FileNotFoundError, ValueError, ssl.SSLError) as e_ssl:
                logger.warning(f"⚠️ SSL configuration failed: {str(e_ssl)}. Falling back to HTTP.")
                logger.warning("   Ensure SSL_CERT_PATH and SSL_KEY_PATH in .env are correct and files exist.")
                protocol = 'http' # Explicitly set back to http on SSL failure
            except Exception as e_ssl_other:
                logger.error(f"⚠️ An unexpected error occurred during SSL setup: {str(e_ssl_other)}. Falling back to HTTP.", exc_info=True)
                protocol = 'http'
        else:
            logger.info("SSL_CERT_PATH and/or SSL_KEY_PATH not configured. Running in HTTP mode.")
            protocol = 'http'
            
        actual_wsdl_url = Config.get_wsdl_url() # Get WSDL URL based on final protocol and config

        logger.info(f"\n🌍 Starting SOAP server at {protocol}://{host}:{port}")
        logger.info(f"   WSDL available at: {actual_wsdl_url}")
        logger.info(f"⚙️  System mode: {Config.SYSTEM_MODE}")
        logger.info("🛑 Press Ctrl+C to stop\n")
        
        server.serve_forever()

    except KeyboardInterrupt:
        logger.info("\n🛑 Server stopped by user (Ctrl+C).")
    except RuntimeError as e_runtime: # Catch specific runtime errors like DataSecurity init failure
        logger.critical(f"💥 Critical runtime error preventing server start: {str(e_runtime)}", exc_info=True)
        sys.exit(1)
    except Exception as e_start:
        logger.critical(f"💥 Critical error starting server: {str(e_start)}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    run_server()
