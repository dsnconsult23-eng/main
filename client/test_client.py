
#!/usr/bin/env python3
import os
import sys
import ssl # Not directly used for context, but good to have if extending SSL
from zeep import Client, Settings
from zeep.transports import Transport
from zeep.exceptions import Fault
from requests import Session
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3
import logging
from typing import Dict, Any, Optional
from lxml import etree # For parsing fault detail if needed

# Add project root for client to sys.path if modules are not installed
project_root_client = os.path.dirname(os.path.abspath(__file__))
project_root_base = os.path.dirname(project_root_client)
if project_root_base not in sys.path:
    sys.path.insert(0, project_root_base)
if project_root_client not in sys.path:
    sys.path.insert(0, project_root_client)

from client.config import Config
from client.crypto_utils import encrypt_3des_ecb_pkcs7, decrypt_3des_ecb_pkcs7

logging.basicConfig(
    level=Config.LOG_LEVEL,
    format=Config.LOG_FORMAT,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

if Config.CLIENT_SSL_VERIFY is False:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    logger.warning("SSL warnings disabled because CLIENT_SSL_VERIFY is False.")


class InsuranceSoapCliTestClient:
    def __init__(self):
        try:
            self._validate_config()
            self.wsdl_url = Config.get_wsdl_url()
            logger.info(f"Attempting to connect to WSDL: {self.wsdl_url}") # Log URL being used
            self.transport = self._configure_transport()
            self.client = self._initialize_zeep_client()
            logger.info(f"SOAP test client initialized successfully for WSDL: {self.wsdl_url}")
        except Exception as e:
            logger.critical("Failed to initialize SOAP test client during __init__", exc_info=True)
            raise # Re-raise to make it clear initialization failed

    def _validate_config(self):
        if Config.SECRET_KEY == '!!!MISSING_SECRET_KEY_IN_ENV!!!' or \
           Config.SERVICE_USER == '!!!MISSING_SERVICE_USER_IN_ENV!!!' or \
           Config.SERVICE_PASSWORD == '!!!MISSING_SERVICE_PASSWORD_IN_ENV!!!':
            raise ValueError("Critical config (SECRET_KEY, SERVICE_USER, SERVICE_PASSWORD) missing in .env for client.")
        
        if Config.SYSTEM_MODE == "LIVE":
            if Config.CLIENT_SSL_VERIFY is False:
                logger.warning("Client is configured for LIVE system but CLIENT_SSL_VERIFY is False. This is insecure.")
            elif isinstance(Config.CLIENT_SSL_VERIFY, str) and not os.path.exists(Config.CLIENT_SSL_VERIFY):
                 logger.error(f"Client is configured for LIVE system and CLIENT_SSL_VERIFY is a path, but file not found: {Config.CLIENT_SSL_VERIFY}")
                 # Depending on policy, you might raise an error here for LIVE mode
            elif Config.CLIENT_SSL_VERIFY is True: # Boolean True
                 logger.info("Client is configured for LIVE system with CLIENT_SSL_VERIFY=True (uses default CAs).")


    def _configure_transport(self) -> Transport:
        retry_strategy = Retry(
            total=3, connect=3, read=3,
            backoff_factor=0.5, # Shorter backoff for quicker retries in test
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=frozenset(['POST', 'GET']) # Zeep uses GET for WSDL
        )
        
        session = Session()
        
        # SSL Verification logic based on processed Config.CLIENT_SSL_VERIFY
        if isinstance(Config.CLIENT_SSL_VERIFY, str):
            # This means it's a path string (since "true"/"false" were converted to bools in Config)
            if not os.path.exists(Config.CLIENT_SSL_VERIFY):
                logger.error(f"CLIENT_SSL_VERIFY path '{Config.CLIENT_SSL_VERIFY}' not found. SSL connections might fail or use system CAs.")
                # If the path is for a self-signed cert and it's missing, HTTPS will likely fail verification.
                # Setting session.verify to the non-existent path will cause requests to error out if it's used for HTTPS.
                # For an HTTP URL, this setting is largely ignored by requests.
                session.verify = Config.CLIENT_SSL_VERIFY # Let requests handle the missing path if it becomes relevant
            else:
                session.verify = Config.CLIENT_SSL_VERIFY
                logger.info(f"SSL verification will use CA/cert at: {Config.CLIENT_SSL_VERIFY}")
        elif isinstance(Config.CLIENT_SSL_VERIFY, bool):
            session.verify = Config.CLIENT_SSL_VERIFY
            logger.info(f"SSL verification boolean set to: {Config.CLIENT_SSL_VERIFY}")
        # No 'else' needed as Config.CLIENT_SSL_VERIFY is guaranteed to be str or bool by now

        if Config.CLIENT_SSL_CERT_PATH and Config.CLIENT_SSL_KEY_PATH:
            if os.path.exists(Config.CLIENT_SSL_CERT_PATH) and os.path.exists(Config.CLIENT_SSL_KEY_PATH):
                session.cert = (Config.CLIENT_SSL_CERT_PATH, Config.CLIENT_SSL_KEY_PATH)
                logger.info(f"Using client certificate for mTLS: {Config.CLIENT_SSL_CERT_PATH}")
            else:
                logger.warning("Client SSL cert/key paths for mTLS provided but files not found.")
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        return Transport(
            session=session,
            timeout=Config.REQUEST_TIMEOUT, # General timeout for operations
            operation_timeout=Config.REQUEST_TIMEOUT + 10 # More specific for Zeep
        )

    def _initialize_zeep_client(self) -> Client:
        zeep_settings = Settings(
            strict=False,
            xml_huge_tree=True,
        )
        try:
            logger.debug(f"Zeep attempting to load WSDL from: {self.wsdl_url} with timeout {self.transport.load_timeout}")
            zeep_client = Client(
                wsdl=self.wsdl_url,
                transport=self.transport,
                settings=zeep_settings
            )
            logger.info("Zeep client created successfully.")
            return zeep_client
        except requests.exceptions.ConnectionError as conn_err:
            logger.error(f"Zeep client ConnectionError during WSDL load from {self.wsdl_url}: {conn_err}", exc_info=True)
            raise # Re-raise to be caught by __init__
        except Exception as e:
            logger.error(f"Zeep client failed to initialize for WSDL {self.wsdl_url}: {str(e)}", exc_info=True)
            raise

    def _encrypt_payload(self, xml_str: str) -> str:
        try:
            return encrypt_3des_ecb_pkcs7(Config.SECRET_KEY, xml_str)
        except Exception as e:
            logger.error("Client-side encryption failed", exc_info=True)
            raise ValueError("Failed to encrypt XML data for request") from e

    def _decrypt_payload(self, encrypted_str: str) -> str:
        if not encrypted_str:
            return ""
        try:
            return decrypt_3des_ecb_pkcs7(Config.SECRET_KEY, encrypted_str)
        except Exception as e:
            logger.error(f"Client-side decryption failed for payload: '{encrypted_str[:100]}...'", exc_info=True)
            raise ValueError("Failed to decrypt XML response from server") from e

    def send_request(self, request_type: str, xml_data: str) -> Dict[str, Any]:
        try:
            logger.info(f"Preparing to send '{request_type}' request.")
            logger.debug(f"Plaintext XML for '{request_type}':\n{xml_data}")
            encrypted_xml = self._encrypt_payload(xml_data)
        
            # Add debug logging for the request
            logger.debug(f"Sending request with parameters: "
                    f"User={Config.SERVICE_USER}, "
                    f"RequestType={request_type}, "
                    f"XMLData length={len(encrypted_xml)}")
        
            response_obj = self.client.service.SendRequest(
            UserName=Config.SERVICE_USER,
            Password=Config.SERVICE_PASSWORD,
            RequestType=request_type,
            XMLData=encrypted_xml
        )

        # Enhanced response logging
            logger.debug(f"Raw response object: {response_obj}")
            logger.debug(f"Response attributes: {dir(response_obj)}")
        
            status_code = getattr(response_obj, 'Status', None)
            error_message = getattr(response_obj, 'Error', None)
            response_type_echo = getattr(response_obj, 'RequestTypeOut', None)
            encrypted_result_xml = getattr(response_obj, 'XMLResult', None)

            logger.info(f"Received response for '{request_type}': "
                   f"Status='{status_code}', Error='{error_message}', "
                   f"TypeEcho='{response_type_echo}', "
                   f"XMLResult length={len(encrypted_result_xml) if encrypted_result_xml else 0}")

            decrypted_xml_result = ""
            if encrypted_result_xml:
                try:
                    decrypted_xml_result = self._decrypt_payload(encrypted_result_xml)
                    if status_code == '1':
                        logger.info(f"Decrypted success XMLResult for '{request_type}':\n{decrypted_xml_result}")
                    else: # status_code is '0' or other, but XMLResult was present
                        logger.info(f"Decrypted XMLResult (Status {status_code}) for '{request_type}':\n{decrypted_xml_result}")
                except ValueError as e_dec: # Catch our specific decryption value error
                    logger.error(f"Error decrypting XMLResult for '{request_type}': {e_dec}")
                    # Keep original error_message if present, or note decryption failure
                    if not error_message:
                         error_message = f"Response XMLResult decryption failed: {e_dec}"
            
            return {
                'status_code': status_code,
                'error_message': error_message,
                'request_type_echo': response_type_echo,
                'decrypted_xml_result': decrypted_xml_result,
                'raw_encrypted_xml_result': encrypted_result_xml
            }
            
        except Fault as f:
            logger.error(f"SOAP Fault for '{request_type}': Code={f.code}, Message={f.message}", exc_info=True)
            detail_str = etree.tostring(f.detail, pretty_print=True).decode() if f.detail is not None else None
            return {
                'status_code': 'FAULT', 'error_message': f.message, 
                'fault_code': str(f.code), 'fault_detail': detail_str,
                'request_type_echo': request_type, 'decrypted_xml_result': None
            }
        except requests.exceptions.ConnectionError as conn_err: # Catch connection errors specifically
            logger.error(f"ConnectionError during '{request_type}' request to {self.wsdl_url}: {conn_err}", exc_info=True)
            return {
                'status_code': 'CONNECTION_ERROR', 'error_message': str(conn_err),
                'request_type_echo': request_type, 'decrypted_xml_result': None
            }
        except Exception as e:
            logger.error(f"Unexpected error during '{request_type}' request: {str(e)}", exc_info=True)
            return {
                'status_code': 'CLIENT_EXCEPTION', 'error_message': str(e),
                'request_type_echo': request_type, 'decrypted_xml_result': None
            }

# ... (print_service_call_result and main_test_suite function remain the same as previously provided) ...
# Ensure main_test_suite uses the corrected class name: client = InsuranceSoapCliTestClient()
def test_send_claim():
    logger.info("Starting SendClaim test...")
    try:
        client = InsuranceSoapCliTestClient()
    except Exception as e:
        logger.critical(f"Failed to initialize client: {e}", exc_info=True)
        return

    # Test data
    test_claim_id = "PPIMKC0000001/25"
    test_policy_number = "POLICY#TEST"
    claim_type = "DEATH_ACC"
    
    send_claim_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<root>
  <GACClaimID>{test_claim_id}</GACClaimID>
  <PolicyNumber>{test_policy_number}</PolicyNumber>
  <ReportClaim>
    <ClaimRegistrationCreated>2025-02-07T14:26:00+01:00</ClaimRegistrationCreated>
    <CurrencyCode>MKD</CurrencyCode>
    <ClaimDate>2025-02-01T00:00:00+01:00</ClaimDate>
    <Type>{claim_type}</Type>
    <ClaimDescription>Test claim description</ClaimDescription>
    <ClaimPlace_CountryCode>HU</ClaimPlace_CountryCode>
    <ClaimPlace_Address>Test Address 123</ClaimPlace_Address>
    <Beneficiary_Individual>INDIVIDUAL</Beneficiary_Individual>
    <Beneficiary_LastName>Beneficiary</Beneficiary_LastName>
    <Beneficiary_FirstName>Test</Beneficiary_FirstName>
    <Beneficiary_CountryCode>HU</Beneficiary_CountryCode>
    <Beneficiary_Zip>1062</Beneficiary_Zip>
    <Beneficiary_City>BUDAPEST</Beneficiary_City>
    <Beneficiary_Address>Test Address 123</Beneficiary_Address>
    <Beneficiary_Street>Test Street</Beneficiary_Street>
    <Beneficiary_PhoneNumber1>+3612345678</Beneficiary_PhoneNumber1>
    <Beneficiary_Email>beneficiary@example.com</Beneficiary_Email>
    <Documents></Documents>
  </ReportClaim>
</root>"""

    result_send_claim = client.send_request('SendClaim', send_claim_xml)
    print_service_call_result("SendClaim", result_send_claim)

    if result_send_claim.get('status_code') == '1' and result_send_claim.get('decrypted_xml_result'):
        try:
            res_xml_root = etree.fromstring(result_send_claim['decrypted_xml_result'].encode('utf-8'))
            uniqa_claim_node = res_xml_root.find("UniqaClaimID")
            if uniqa_claim_node is not None and uniqa_claim_node.text:
                logger.info(f"Successfully created claim with UniqaClaimID: {uniqa_claim_node.text}")
        except Exception as e:
            logger.error("Failed to parse SendClaim response", exc_info=True)


def print_service_call_result(service_name: str, result: Dict[str, Any]):
    """Print formatted service call result."""
    print(f"\n--- Test Result for: {service_name} ---")
    print(f"  Status Code         : {result.get('status_code')}")
    if result.get('error_message'):
        print(f"  Error Message       : {result.get('error_message')}")
    if result.get('fault_code'):
        print(f"  Fault Code          : {result.get('fault_code')}")
        if result.get('fault_detail'):
            print(f"  Fault Detail        :\n{result.get('fault_detail')}")
    print(f"  Request Type Echo   : {result.get('request_type_echo')}")
    if result.get('decrypted_xml_result'):
        print(f"  Decrypted XML Result:\n{result.get('decrypted_xml_result')}")
    elif result.get('raw_encrypted_xml_result') and not result.get('decrypted_xml_result'):
        print(f"  Raw Encrypted XML (Decryption Failed/Skipped):\n{result.get('raw_encrypted_xml_result')[:200]}...")
    print("--- End of Result ---")

def main_test_suite():
    logger.info("Starting main test suite for InsuranceSoapCliTestClient...")
    try:
        client = InsuranceSoapCliTestClient() # Use the corrected class name
    except Exception as e:
        logger.critical(f"Failed to initialize the test client. Aborting test suite. Error: {e}", exc_info=True)
        sys.exit(1)

    # 1. Test SendRegistration
    send_reg_xml = """<?xml version="1.0" encoding="utf-8"?>
<root>
  <Partner>Iute Credit Macedonia DOOEL Skopje</Partner>
  <GACID>PPIMK0000001/25</GACID>
  <CertificateID>PPIMK0000001/25</CertificateID>
  <Insured>
    <PartnerReferenceID>#REFID_TESTCLIENT</PartnerReferenceID>
    <PersonType>1</PersonType>
    <VATNumber></VATNumber>
    <Title>Dr.</Title>
    <LastName>TesterClient</LastName>
    <FirstName>John</FirstName>
    <Country>HU</Country>
    <ZIP>1062</ZIP>
    <State>Pest</State>
    <City>BUDAPEST</City>
    <Street>Test Utca 123</Street>
    <BirthPlace>BUDAPEST</BirthPlace>
    <BirthDateDMY>01-01-1980</BirthDateDMY>
    <Gender>Male</Gender>
    <Phone>+3612345678</Phone>
    <Email>john.tester.client@example.com</Email>
  </Insured>
  <Policy>
    <Cover>Sigurimi i Mbrojtjes se Kredise +</Cover>
    <ValidFrom>01-06-2025</ValidFrom>
    <ValidTo>01.06.2027</ValidTo>
    <ValidToSMO>01-06-2026</ValidToSMO>
    <CurrencyCode>MKD</CurrencyCode>
    <SumInsured>100000.00</SumInsured>
    <SumInsuredEUR>1625.18</SumInsuredEUR>
    <Premium>4800.00</Premium>
    <AdditionalPremium>333.29</AdditionalPremium>
    <GrossPremium>5133.29</GrossPremium>
  </Policy>
</root>"""
    result_send_reg = client.send_request('SendRegistration', send_reg_xml)
    print_service_call_result("SendRegistration", result_send_reg)

    gacid_for_test = "PPIMK0000001/25"
    policy_number_for_test: Optional[str] = None
    uniqa_offer_id_for_test: Optional[str] = None

    if result_send_reg.get('status_code') == '1' and result_send_reg.get('decrypted_xml_result'):
        try:
            res_xml_root = etree.fromstring(result_send_reg['decrypted_xml_result'].encode('utf-8'))
            policy_num_node = res_xml_root.find("PolicyNumber")
            if policy_num_node is not None and policy_num_node.text:
                policy_number_for_test = policy_num_node.text
            uniqa_offer_node = res_xml_root.find("UniqaOfferID")
            if uniqa_offer_node is not None and uniqa_offer_node.text:
                uniqa_offer_id_for_test = uniqa_offer_node.text
        except Exception: print("Some Exception!") # Silently ignore parsing errors for test data extraction

    # Add other tests (GetStatus, ChangeRegistration, etc.) here, using extracted data
#     # ... (Example for GetStatus) ...
#     if gacid_for_test:
#         get_status_xml = f"""<?xml version="1.0" encoding="utf-8"?>
# <root>
#   <GACID>{gacid_for_test}</GACID>
#   {f"<UniqaOfferID>{uniqa_offer_id_for_test}</UniqaOfferID>" if uniqa_offer_id_for_test else ""}
# </root>"""
#         result_get_status = client.send_request('GetStatus', get_status_xml)
#         print_service_call_result("GetStatus", result_get_status)

    logger.info("Test suite finished.")


if __name__ == '__main__':
    test_send_claim()