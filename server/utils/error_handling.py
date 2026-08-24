from typing import Dict, Any
from spyne import Fault
from lxml import etree
from security.encryption import DataSecurity

def handle_soap_error(error: Exception, request_type: str) -> Dict[str, Any]:
    """
    Handle SOAP errors and return proper response structure
    
    Args:
        error: The exception that occurred
        request_type: The type of SOAP request being processed
        
    Returns:
        Dictionary with error response structure
    """
    error_message = str(error)
    data_security = DataSecurity()
    
    # Create error response XML
    error_xml = f"""<?xml version="1.0" encoding="utf-8"?>
    <root>
        <Error>{error_message}</Error>
    </root>"""
    
    # Encrypt the error response
    encrypted_error = data_security.encrypt_xml(error_xml)
    
    return {
        'Status': '0',
        'Error': error_message,
        'RequestType': request_type,
        'XMLResult': encrypted_error
    }

def create_soap_fault(error: Exception) -> Fault:
    """
    Create a SOAP Fault response for unhandled exceptions
    
    Args:
        error: The exception that occurred
        
    Returns:
        SOAP Fault object
    """
    return Fault(
        faultcode='Server',
        faultstring=str(error),
        detail=etree.tostring(etree.Element('detail')))