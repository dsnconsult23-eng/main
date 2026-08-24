from spyne import ServiceBase, rpc, Unicode
from lxml import etree
from security.encryption import DataSecurity
from security.authentication import Authenticator
from models.policy import GetStatusInputData, GetStatusOutputData
from models.storno import StornoInputData, StornoOutputData
from models.change_registration import ChangeRegistrationInputData, ChangeRegistrationOutputData
from models.claim import SendClaimInputData, SendClaimOutputData, GetClaimStatusInputData, GetClaimStatusOutputData
from config import Config
from models.document_payloads import extract_document_payloads
import logging
def parse_registration_xml(xml_root):
        """
        Parses XML and returns a dictionary structured for insert_polisa_sertifikati().
        """

        def get_text(node, default=""):
            return node.text.strip() if node is not None and node.text else default

        def get_date(node_name):
            val = xml_root.findtext(node_name)
            return val.replace('/', '.').strip() if val else None

        # Top-level attributes
        parsed_data = {
            "Partner": xml_root.findtext("Partner") or "",
            "GACID": xml_root.findtext("GACID") or "",
            "CertificateID": xml_root.findtext("CertificateID") or "",
            "Documents": extract_document_payloads(xml_root.find("Documents")),
            "Insured": {},
            "Policy": {}
        }

        # Insured section
        insured_node = xml_root.find("Insured")
        if insured_node is not None:
            parsed_data["Insured"] = {
                "PartnerReferenceID": get_text(insured_node.find("PartnerReferenceID")),
                "PersonType": get_text(insured_node.find("PersonType")) or "1",
                "VATNumber": get_text(insured_node.find("VATNumber")) or None,
                "Title": get_text(insured_node.find("Title")),
                "LastName": get_text(insured_node.find("LastName")),
                "FirstName": get_text(insured_node.find("FirstName")),
                "Country": get_text(insured_node.find("Country")),
                "ZIP": get_text(insured_node.find("ZIP")),
                "State": get_text(insured_node.find("State")),
                "City": get_text(insured_node.find("City")),
                "Street": get_text(insured_node.find("Street")),
                "BirthPlace": get_text(insured_node.find("BirthPlace")),
                "BirthDateDMY": get_text(insured_node.find("BirthDateDMY")),  # expects D.M.Y
                "Gender": get_text(insured_node.find("Gender")),
                "Phone": get_text(insured_node.find("Phone")),
                "Email": get_text(insured_node.find("Email")),
            }

        # Policy section
        policy_node = xml_root.find("Policy")
        if policy_node is not None:
            parsed_data["Policy"] = {
                "Cover": get_text(policy_node.find("Cover")),
                "ValidFrom": get_date("Policy/ValidFrom"),
                "ValidTo": get_date("Policy/ValidTo"),
                "ValidToSMO": get_date("Policy/ValidToSMO"),
                "CurrencyCode": get_text(policy_node.find("CurrencyCode")),
                "SumInsured": get_text(policy_node.find("SumInsured")) or "0",
                "SumInsuredEUR": get_text(policy_node.find("SumInsuredEUR")) or "0",
                "Premium": get_text(policy_node.find("Premium")) or "0",
                "AdditionalPremium": get_text(policy_node.find("AdditionalPremium")) or "0",
                "GrossPremium": get_text(policy_node.find("GrossPremium")) or "0"
            }

        return parsed_data
