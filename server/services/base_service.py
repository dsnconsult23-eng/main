from spyne import ServiceBase
from typing import Dict, Any
from ..security.encryption import TripleDESEncryptor
from ..security.authentication import Authenticator
from ..utils.error_handling import handle_soap_error

class BaseInsuranceService(ServiceBase):
    def __init__(self):
        self.encryptor = TripleDESEncryptor()
        self.authenticator = Authenticator()

    def _authenticate(self, username: str, password: str) -> None:
        if not self.authenticator.authenticate(username, password):
            raise PermissionError("Authentication failed")

    def _encrypt_response(self, xml_data: str) -> str:
        return self.encryptor.encrypt(xml_data)

    def _decrypt_request(self, encrypted_xml: str) -> str:
        try:
            return self.encryptor.decrypt(encrypted_xml)
        except Exception as e:
            raise ValueError("Invalid Secret key or XML data") from e

    def _create_error_response(self, error_message: str, request_type: str) -> Dict[str, Any]:
        return {
            'Status': '0',
            'Error': error_message,
            'RequestType': request_type,
            'XMLResult': ''
        }

    def _create_success_response(self, xml_result: str, request_type: str) -> Dict[str, Any]:
        return {
            'Status': '1',
            'Error': '',
            'RequestType': request_type,
            'XMLResult': self._encrypt_response(xml_result)
        }