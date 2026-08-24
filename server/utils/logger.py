# soap-web-services/server/utils/logger.py
import logging
import sys
import os
# Assuming config.py is in the parent directory of utils/ or project_root is in sys.path
# from ..config import Config # If utils is a proper submodule
from config import Config # Relies on sys.path setup in app.py

def setup_logging():
    """
    Configures centralized root logging for the application based on Config.
    This should be called once at the beginning of the application.
    """
    root_logger = logging.getLogger() # Get the root logger

    # Clear existing handlers from the root logger to prevent duplicate messages
    if root_logger.hasHandlers():
        for handler in root_logger.handlers[:]: # Iterate over a copy
            root_logger.removeHandler(handler)
            handler.close() # Close handler to release resources like file locks

    log_level_name = Config.LOG_LEVEL
    log_level = getattr(logging, log_level_name.upper(), logging.INFO) # Default to INFO
    root_logger.setLevel(log_level) # Set the threshold for the root logger FIRST

    formatter = logging.Formatter(Config.LOG_FORMAT)

    # Console Handler (always add for visibility, e.g., during startup or if file logging fails)
    ch = logging.StreamHandler(sys.stdout) # Log to stdout
    ch.setFormatter(formatter)
    ch.setLevel(log_level) # Handler level should also be set
    root_logger.addHandler(ch)

    # Optional: File Handler
    if Config.LOG_FILE_PATH:
        try:
            log_dir = os.path.dirname(Config.LOG_FILE_PATH)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
                print(f"Log directory created: {log_dir}") # Print for immediate feedback

            fh = logging.FileHandler(Config.LOG_FILE_PATH, mode='a', encoding='utf-8') # Append mode, utf-8
            fh.setFormatter(formatter)
            fh.setLevel(log_level) # Handler level
            root_logger.addHandler(fh)
        except Exception as e:
            # If file logger setup fails, this will be logged to the console handler (if already added)
            # or print as a last resort.
            root_logger.error(f"Failed to configure file logger at {Config.LOG_FILE_PATH}: {str(e)}", exc_info=True)
            print(f"ERROR: Failed to configure file logger at {Config.LOG_FILE_PATH}: {str(e)}", file=sys.stderr)


    # Log confirmation message (will go to all configured handlers)
    # This also tests that the logging setup itself is working.
    initial_log_message_parts = [
        f"Root logging configured. Level: {log_level_name}.",
        "Output to console."
    ]
    if Config.LOG_FILE_PATH and any(isinstance(h, logging.FileHandler) for h in root_logger.handlers):
        initial_log_message_parts.append(f"Output to file: {Config.LOG_FILE_PATH}.")
    
    # Use the root_logger directly here or logging.info which uses the root logger by default if no other logger is named.
    logging.info(" ".join(initial_log_message_parts))


    # Optionally, set levels for verbose third-party loggers
    logging.getLogger('spyne.protocol').setLevel(logging.WARNING) # Spyne can be very verbose
    logging.getLogger('zeep').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)