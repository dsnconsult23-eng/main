import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from lxml import etree

from config import Config
from db.database import _convert_eml_to_pdf_bytes, _detect_claim_document_extension, save_claim_documents
from models.claim import SendClaimInputData
from services.soap_service import InsuranceSoapService


EML_BYTES = (
    b"From: sender@example.com\r\n"
    b"To: receiver@example.com\r\n"
    b"Subject: SendClaim test\r\n"
    b"MIME-Version: 1.0\r\n"
    b"Content-Type: text/plain; charset=utf-8\r\n\r\n"
    b"Hello from the EML document."
)


def build_send_claim_xml() -> etree._Element:
    encoded_eml = base64.b64encode(EML_BYTES).decode("ascii")
    encoded_pdf = base64.b64encode(b"%PDF-1.4\n%%EOF\n").decode("ascii")
    xml = f"""
    <root>
      <GACID>PPIMK0000001/25</GACID>
      <PolicyNumber>40/013961</PolicyNumber>
      <ReportClaim>
        <ClaimRegistrationCreated>2026-05-12T09:00:00+02:00</ClaimRegistrationCreated>
        <CurrencyCode>MKD</CurrencyCode>
        <ClaimDate>2026-05-12T00:00:00+02:00</ClaimDate>
        <Type>INCAPACITY_ILL</Type>
        <ClaimDescription>SendClaim document test</ClaimDescription>
        <ClaimPlace_CountryCode>MK</ClaimPlace_CountryCode>
        <ClaimPlace_Address>Skopje</ClaimPlace_Address>
        <Beneficiary_Individual>INDIVIDUAL</Beneficiary_Individual>
        <Beneficiary_LastName>Petrov</Beneficiary_LastName>
        <Beneficiary_FirstName>Marko</Beneficiary_FirstName>
        <Beneficiary_CountryCode>MK</Beneficiary_CountryCode>
        <Beneficiary_Zip>1000</Beneficiary_Zip>
        <Beneficiary_City>Skopje</Beneficiary_City>
        <Beneficiary_Address>Partizanska 1</Beneficiary_Address>
        <Beneficiary_Street>Partizanska</Beneficiary_Street>
        <Beneficiary_PhoneNumber1>070123456</Beneficiary_PhoneNumber1>
        <Beneficiary_Email>marko.petrov@test.mk</Beneficiary_Email>
        <Documents>
          <Eml>{encoded_eml}</Eml>
          <PDF>{encoded_pdf}</PDF>
        </Documents>
      </ReportClaim>
    </root>
    """
    return etree.fromstring(xml.encode("utf-8"))


class FakeCursor:
    def __init__(self):
        self.executions = []
        self.closed = False

    def execute(self, sql, params):
        self.executions.append((sql, params))

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self):
        self.commits = 0
        self.closed = False

    def commit(self):
        self.commits += 1

    def close(self):
        self.closed = True


class SendClaimDocumentTests(unittest.TestCase):
    def test_send_claim_accepts_all_supported_document_tags(self):
        root = build_send_claim_xml()
        documents = root.find("ReportClaim/Documents")
        documents.clear()
        for index, tag in enumerate(("Pdf", "PDF", "Document", "Email", "Eml", "EML")):
            etree.SubElement(documents, tag).text = base64.b64encode(
                f"document-{index}".encode("ascii")
            ).decode("ascii")

        parsed = SendClaimInputData.from_xml_element(root)
        self.assertEqual(6, len(parsed.ReportClaim.Documents))

    def test_xml_parser_accepts_eml_and_pdf_tags(self):
        parsed = SendClaimInputData.from_xml_element(build_send_claim_xml())
        self.assertEqual(2, len(parsed.ReportClaim.Documents))
        self.assertEqual(EML_BYTES, base64.b64decode(parsed.ReportClaim.Documents[1]))

    def test_eml_is_converted_and_saved_as_pdf(self):
        parsed = SendClaimInputData.from_xml_element(build_send_claim_xml())
        cursor = FakeCursor()
        connection = FakeConnection()

        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            Config, "CLAIM_DOCUMENT_STORAGE_PATH", temp_dir
        ):
            save_claim_documents(
                parsed.model_dump(), "40/013961", "CLAIM-001", cursor, connection
            )
            saved_files = sorted(Path(temp_dir).rglob("*.*"))
            self.assertEqual(2, len(saved_files))
            self.assertTrue(all(path.suffix == ".pdf" for path in saved_files))
            self.assertTrue(all(path.read_bytes().startswith(b"%PDF") for path in saved_files))
            self.assertEqual(2, len(cursor.executions))

        self.assertEqual(".eml", _detect_claim_document_extension(EML_BYTES))
        self.assertTrue(_convert_eml_to_pdf_bytes(EML_BYTES).startswith(b"%PDF-1.4"))

    def test_send_claim_handler_passes_documents_to_storage(self):
        first_connection, second_connection = FakeConnection(), FakeConnection()
        first_cursor, second_cursor = FakeCursor(), FakeCursor()
        database_results = [
            (first_connection, first_cursor, True),
            (second_connection, second_cursor, True),
        ]
        procedure_result = {
            "result": (1, "PPIMK0000001/25", "40/013961", 1, "OK", "CLAIM-001")
        }

        with patch("services.soap_service.connect_informix", side_effect=database_results), \
             patch("services.soap_service.insert_claim_data"), \
             patch("services.soap_service.call_generiraj_polisa_claim", return_value=procedure_result), \
             patch("services.soap_service.save_claim_documents") as save_documents:
            response = InsuranceSoapService()._handle_send_claim(build_send_claim_xml())

        save_documents.assert_called_once()
        saved_claim = save_documents.call_args.args[0]
        self.assertEqual(2, len(saved_claim["ReportClaim"]["Documents"]))
        response_xml = etree.fromstring(response.encode("utf-8"))
        self.assertEqual("CLAIM-001", response_xml.findtext("SendClaim/UniqaClaimID"))


if __name__ == "__main__":
    unittest.main()
