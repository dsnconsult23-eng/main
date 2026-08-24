# soap-web-services/client/app.py
from flask import Flask, request, jsonify
from zeep import Client, Settings
from zeep.transports import Transport
from requests import Session
import logging # Added for logging
import hashlib # To be used by crypto_utils if not already

# Assuming client/config.py and client/crypto_utils.py are in the same directory or python path is set
from config import Config
from crypto_utils import encrypt_3des_ecb_pkcs7, decrypt_3des_ecb_pkcs7

app = Flask(__name__)

# Configure basic logging for the client app
logging.basicConfig(level=Config.LOG_LEVEL, format=Config.LOG_FORMAT)
logger = logging.getLogger(__name__)

# Initialize SOAP Client (Zeep)
try:
    wsdl_url = Config.get_wsdl_url()
    logger.info(f"SOAP Client connecting to WSDL: {wsdl_url}")
    
    session = Session()
    if isinstance(Config.CLIENT_SSL_VERIFY, str) and Config.CLIENT_SSL_VERIFY.lower() != 'false':
        session.verify = Config.CLIENT_SSL_VERIFY # Path to CA bundle or server cert
    elif isinstance(Config.CLIENT_SSL_VERIFY, bool):
        session.verify = Config.CLIENT_SSL_VERIFY
    else: # Default to True if not 'false' string
        session.verify = True


    if Config.CLIENT_SSL_CERT_PATH and Config.CLIENT_SSL_KEY_PATH:
        session.cert = (Config.CLIENT_SSL_CERT_PATH, Config.CLIENT_SSL_KEY_PATH)

    transport = Transport(session=session, timeout=Config.REQUEST_TIMEOUT)
    
    settings = Settings(strict=False, xml_huge_tree=True) # Match settings from test_client if needed
    soap_client = Client(wsdl=wsdl_url, transport=transport, settings=settings)
    logger.info("SOAP Client initialized successfully.")

except Exception as e:
    logger.critical(f"Failed to initialize SOAP client for Flask app: {e}", exc_info=True)
    # Depending on requirements, the Flask app might not be usable if SOAP client fails.
    # For now, it will raise an error when a route tries to use soap_client if it's None.
    soap_client = None


@app.route('/send_registration_via_flask', methods=['POST']) # Changed route to be more specific
def send_registration_flask():
    if not soap_client:
        logger.error("SOAP client not available for /send_registration_via_flask")
        return jsonify({'error': 'SOAP client not initialized'}), 500

    try:
        # Example: Get data from POST request's JSON body
        # For a real app, validate this input
        # request_data = request.get_json()
        # GACID = request_data.get('GACID')
        # PolicyNumber = request_data.get('PolicyNumber')
        # if not GACID or not PolicyNumber:
        #     return jsonify({'error': 'GACID and PolicyNumber are required in JSON payload'}), 400

        # Build plaintext XML string (example input based on PDF for SendRegistration)
        # This should be dynamically generated based on actual data
        raw_xml_data = f"""<?xml version="1.0" encoding="utf-8"?>
<root>
  <Partner>Test Partner via Flask Client</Partner>
  <GACID>FPFLASK000001/25</GACID>
  <CertificateID>FPFLASK000001/25</CertificateID>
  <Insured>
    <PartnerReferenceID>#FLASKREF001</PartnerReferenceID>
    <PersonType>1</PersonType>
    <VATNumber></VATNumber>
    <Title>Mr.</Title>
    <LastName>FlaskClient</LastName>
    <FirstName>Testy</FirstName>
    <Country>MK</Country>
    <ZIP>1000</ZIP>
    <State>Skopje</State>
    <City>SKOPJE</City>
    <Street>Client Street 1</Street>
    <BirthPlace>SKOPJE</BirthPlace>
    <BirthDateDMY>10-10-1990</BirthDateDMY>
    <Gender>Male</Gender>
    <Phone>+38970123456</Phone>
    <Email>flask.client@example.com</Email>
  </Insured>
  <Policy>
    <Cover>Basic Flask Policy</Cover>
    <ValidFrom>01-01-2025</ValidFrom>
    <ValidTo>01-01-2026</ValidTo>
    <ValidToSMO>01-01-2026</ValidToSMO>
    <CurrencyCode>MKD</CurrencyCode>
    <SumInsured>50000.00</SumInsured>
    <SumInsuredEUR>812.00</SumInsuredEUR>
    <Premium>2000.00</Premium>
    <AdditionalPremium>100.00</AdditionalPremium>
    <GrossPremium>2100.00</GrossPremium>
  </Policy>
</root>"""

        logger.debug(f"Raw XML for SendRegistration: {raw_xml_data}")
        
        # Use the consistent encryption from crypto_utils
        encrypted_xml_payload = encrypt_3des_ecb_pkcs7(Config.SECRET_KEY, raw_xml_data)
        logger.debug(f"Encrypted XML payload: {encrypted_xml_payload[:100]}...")

        # Call the SOAP service's SendRequest method
        # Parameters: UserName, Password, RequestType, XMLData
        response = soap_client.service.SendRequest(
            UserName=Config.SERVICE_USER,
            Password=Config.SERVICE_PASSWORD,
            RequestType='SendRegistration', # Hardcoded for this route
            XMLData=encrypted_xml_payload
        )
        
        logger.info(f"SOAP Response Status: {response.Status}, Error: {response.Error}, Type: {response.RequestTypeOut}")

        # Process response
        # Assuming SendRequestOutput(Status, Error, RequestTypeOut, XMLResult)
        if response.Status != '1': # Error from SOAP service
            logger.error(f"SOAP service returned an error: {response.Error}")
            # Decrypt error XMLResult if populated, as per spec (errors are also encrypted XML)
            error_detail = response.Error
            if response.XMLResult:
                try:
                    decrypted_error_xml = decrypt_3des_ecb_pkcs7(Config.SECRET_KEY, response.XMLResult)
                    logger.info(f"Decrypted error XMLResult: {decrypted_error_xml}")
                    # You might parse this XML to get a more structured error
                    error_detail = f"{response.Error} (Details: {decrypted_error_xml})"
                except Exception as e_dec_err:
                    logger.error(f"Failed to decrypt error XMLResult: {e_dec_err}")
            return jsonify({'error': 'SOAP service error', 'details': error_detail}), 400

        # Success, decrypt XMLResult
        decrypted_response_xml = decrypt_3des_ecb_pkcs7(Config.SECRET_KEY, response.XMLResult)
        logger.info(f"Decrypted success XMLResult: {decrypted_response_xml}")
        
        # Here you might parse decrypted_response_xml into a more usable format (e.g., dict)
        return jsonify({
            'message': 'SendRegistration successful via Flask client',
            'status_from_soap': response.Status,
            'request_type_echo': response.RequestTypeOut,
            'decrypted_response_xml': decrypted_response_xml
        })

    except Exception as e:
        logger.critical(f"Error in /send_registration_via_flask: {e}", exc_info=True)
        return jsonify({'error': 'An unexpected error occurred on the client side', 'details': str(e)}), 500

if __name__ == '__main__':
    # Get port from env or default, suitable for client app
    flask_port = int(os.getenv('FLASK_CLIENT_PORT', '5001'))
    app.run(host='0.0.0.0', port=flask_port, debug=True) # Debug=True for development