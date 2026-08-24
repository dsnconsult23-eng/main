from typing import List

from lxml import etree as ET
from pydantic import BaseModel, field_validator

from models.document_payloads import extract_document_payloads


class SendDocumentsInputData(BaseModel):
    Policy: str
    Documents: List[str] = []

    @field_validator("Documents")
    @classmethod
    def validate_documents(cls, value: List[str]) -> List[str]:
        if value is None:
            return []
        return [doc for doc in value if doc is not None and str(doc).strip()]

    @classmethod
    def from_xml_element(cls, element: ET._Element):
        return cls(
            Policy=element.findtext("Policy"),
            Documents=extract_document_payloads(element.find("Documents")),
        )


class SendDocumentsOutputData(BaseModel):
    Policy: str
    DocumentsCount: int

    def to_xml_element(self) -> ET._Element:
        root = ET.Element("root")
        ET.SubElement(root, "Policy").text = self.Policy
        ET.SubElement(root, "DocumentsCount").text = str(self.DocumentsCount)
        return root
