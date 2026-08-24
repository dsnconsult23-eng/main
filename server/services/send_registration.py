import requests
from lxml import etree
from security.encryption import DataSecurity

class SendRegistration:
    def __init__(self, base_url, username, password, secret_key):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.encryptor = DataSecurity(secret_key)

    def build_registration_xml(self, policy_data: dict) -> str:
        root = etree.Element("root")
        etree.SubElement(root, "Partner").text = policy_data['partner']
        etree.SubElement(root, "GACID").text = policy_data['gacid']
        etree.SubElement(root, "CertificateID").text = policy_data['certificate_id']
        insured = etree.SubElement(root, "Insured")
        etree.SubElement(insured, "PartnerReferenceID").text = policy_data['insured']['partner_reference_id']
        etree.SubElement(insured, "PersonType").text = str(policy_data['insured']['person_type'])
        etree.SubElement(insured, "VATNumber").text = policy_data['insured'].get('vat_number', '')
        etree.SubElement(insured, "Title").text = policy_data['insured']['title']
        etree.SubElement(insured, "LastName").text = policy_data['insured']['last_name']
        etree.SubElement(insured, "FirstName").text = policy_data['insured']['first_name']
        etree.SubElement(insured, "Country").text = policy_data['insured']['country']
        etree.SubElement(insured, "ZIP").text = policy_data['insured']['zip_code']
        etree.SubElement(insured, "State").text = policy_data['insured']['state']
        etree.SubElement(insured, "City").text = policy_data['insured']['city']
        etree.SubElement(insured, "Street").text = policy_data['insured']['street']
        etree.SubElement(insured, "BirthPlace").text = policy_data['insured']['birth_place']
        etree.SubElement(insured, "BirthDateDMY").text = policy_data['insured']['birth_date']
        etree.SubElement(insured, "Gender").text = policy_data['insured'].get('gender', '')
        etree.SubElement(insured, "Phone").text = policy_data['insured']['phone']
        etree.SubElement(insured, "Email").text = policy_data['insured']['email']
        policy = etree.SubElement(root, "Policy")
        etree.SubElement(policy, "Cover").text = policy_data['policy']['cover']
        etree.SubElement(policy, "ValidFrom").text = policy_data['policy']['valid_from']
        etree.SubElement(policy, "ValidTo").text = policy_data['policy']['valid_to']
        etree.SubElement(policy, "ValidToSMO").text = policy_data['policy']['valid_to_smo']
        etree.SubElement(policy, "CurrencyCode").text = policy_data['policy']['currency_code']
        etree.SubElement(policy, "SumInsured").text = str(policy_data['policy']['sum_insured'])
        etree.SubElement(policy, "SumInsuredEUR").text = str(policy_data['policy']['sum_insured_eur'])
        etree.SubElement(policy, "Premium").text = str(policy_data['policy']['premium'])
        etree.SubElement(policy, "AdditionalPremium").text = str(policy_data['policy']['additional_premium'])
        etree.SubElement(policy, "GrossPremium").text = str(policy_data['policy']['gross_premium'])
        return etree.tostring(root, encoding='utf-8', pretty_print=True).decode()

    def send_request(self, policy_data: dict) -> dict:
        xml_data = self.build_registration_xml(policy_data)
        encrypted_xml = self.encryptor.encrypt_xml(xml_data)
        print(f"Encrypted XML: {encrypted_xml}")
        soap_envelope = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ins="insurance.services">
   <soapenv:Header/>
   <soapenv:Body>
      <ins:SendRequest>
         <ins:UserName>{self.username}</ins:UserName>
         <ins:Password>{self.password}</ins:Password>
         <ins:RequestType>SendRegistration</ins:RequestType>
         <ins:XMLData>{encrypted_xml}</ins:XMLData>
      </ins:SendRequest>
   </soapenv:Body>
</soapenv:Envelope>"""
        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': 'insurance.services#SendRequest'
        }
        try:
            response = requests.post(self.base_url, data=soap_envelope, headers=headers, timeout=30)
            response.raise_for_status()
            return self.parse_response(response.content)
        except requests.exceptions.RequestException as e:
            return {'Status': '0', 'Error': str(e)}

    def parse_response(self, response_content: bytes) -> dict:
        try:
            root = etree.fromstring(response_content)
            namespaces = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'ins': 'insurance.services'
            }
            result = root.xpath('//ins:SendRequestResponse/ins:SendRequestResult', namespaces=namespaces)
            if not result:
                return {'Status': '0', 'Error': 'No result found in response'}
            # The actual result is inside CDATA, parse as XML if needed
            import re
            import xml.etree.ElementTree as ET
            cdata = result[0].text
            if cdata:
                xml_result = ET.fromstring(cdata)
                status = xml_result.findtext('Status')
                error = xml_result.findtext('Error')
                request_type = xml_result.findtext('RequestType')
                xml_result_content = xml_result.findtext('XMLResult')
                return {
                    'Status': status,
                    'Error': error,
                    'RequestType': request_type,
                    'XMLResult': xml_result_content,
                }
            else:
                return {'Status': '0', 'Error': 'Empty SendRequestResult'}
        except Exception as e:
            return {'Status': '0', 'Error': f"Response parsing failed: {str(e)}"}
