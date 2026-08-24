from pydantic import BaseModel, field_validator, Field
from lxml import etree as ET
from typing import Optional, List
from datetime import datetime
from models.document_payloads import extract_document_payloads

class ReportClaimData(BaseModel):
    ClaimRegistrationCreated: str  # ISO 8601 format
    CurrencyCode: str
    ClaimDate: str  # ISO 8601 format
    Type: str  # Claim type
    ClaimDescription: str
    ClaimPlace_CountryCode: str  # ISO 3166-1 alpha-2
    ClaimPlace_Address: str
    Beneficiary_Individual: str
    Beneficiary_LastName: str
    Beneficiary_FirstName: str
    Beneficiary_CountryCode: str  # ISO 3166-1 alpha-2
    Beneficiary_Zip: str
    Beneficiary_City: str
    Beneficiary_Address: str
    Beneficiary_Street: str
    Beneficiary_PhoneNumber1: str
    Beneficiary_Email: str
    Documents: List[str] = []  # List of base64-encoded PDFs (renamed from PDFs to Documents)

    @field_validator('Type')
    @classmethod
    def validate_claim_type(cls, v: str) -> str:
        valid_types = {
            'DEATH_ACC', 'DEATH_NAT', 'DISABILITY',
            'HOSPITALIZATION_ACC', 'HOSPITALIZATION_ILL',
            'INCAPACITY_ACC', 'INCAPACITY_ILL'
        }
        if v not in valid_types:
            raise ValueError(f"Invalid claim type. Must be one of: {valid_types}")
        return v

    @field_validator('Documents')
    @classmethod
    def validate_documents(cls, v: List[str]) -> List[str]:
        """Validate and clean the Documents list"""
        if v is None:
            return []
        return [doc for doc in v if doc is not None and doc.strip() != '']

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SendClaimInputData(BaseModel):
    GACID: str
    PolicyNumber: str
    ReportClaim: ReportClaimData
    
    @classmethod
    def from_xml_element(cls, element: ET._Element):
        report_claim_element = element.find("ReportClaim")
        if report_claim_element is None:
            raise ValueError("ReportClaim element is required")

        documents = []
        documents.extend(extract_document_payloads(report_claim_element.find("Documents")))
        documents.extend(extract_document_payloads(report_claim_element.find("PDFs")))
        
        return cls(
            GACID=element.findtext("GACID"),
            PolicyNumber=element.findtext("PolicyNumber"),
            ReportClaim=ReportClaimData(
                ClaimRegistrationCreated=report_claim_element.findtext("ClaimRegistrationCreated"),
                CurrencyCode=report_claim_element.findtext("CurrencyCode"),
                ClaimDate=report_claim_element.findtext("ClaimDate"),
                Type=report_claim_element.findtext("Type"),
                ClaimDescription=report_claim_element.findtext("ClaimDescription"),
                ClaimPlace_CountryCode=report_claim_element.findtext("ClaimPlace_CountryCode"),
                ClaimPlace_Address=report_claim_element.findtext("ClaimPlace_Address"),
                Beneficiary_Individual=report_claim_element.findtext("Beneficiary_Individual"),
                Beneficiary_LastName=report_claim_element.findtext("Beneficiary_LastName"),
                Beneficiary_FirstName=report_claim_element.findtext("Beneficiary_FirstName"),
                Beneficiary_CountryCode=report_claim_element.findtext("Beneficiary_CountryCode"),
                Beneficiary_Zip=report_claim_element.findtext("Beneficiary_Zip"),
                Beneficiary_City=report_claim_element.findtext("Beneficiary_City"),
                Beneficiary_Address=report_claim_element.findtext("Beneficiary_Address"),
                Beneficiary_Street=report_claim_element.findtext("Beneficiary_Street"),
                Beneficiary_PhoneNumber1=report_claim_element.findtext("Beneficiary_PhoneNumber1"),
                Beneficiary_Email=report_claim_element.findtext("Beneficiary_Email"),
                Documents=documents
            )
        )


class SendClaimOutputData(BaseModel):
    GACID: str
    PolicyNumber: str
    UniqaClaimID: str
    
    def to_xml_element(self) -> ET._Element:
        root = ET.Element("root")  # Add root element
        send_claim_output = ET.SubElement(root, "SendClaim")
        ET.SubElement(send_claim_output, "GACID").text = self.GACID
        ET.SubElement(send_claim_output, "PolicyNumber").text = self.PolicyNumber
        ET.SubElement(send_claim_output, "UniqaClaimID").text = self.UniqaClaimID
        return root


class ClaimStatusOutput(BaseModel):
    StatusCode: int
    StatusDescription: str


class GetClaimStatusInputData(BaseModel):
    GACID: str
    PolicyNumber: Optional[str] = None
    UniqaClaimID: Optional[str] = Field(default=None, alias="UniqaClaimID")

    class Config:
        populate_by_name = True


class GetClaimStatusOutputData(BaseModel):
    GACID: str
    PolicyNumber: str
    UniqaClaimID: str = Field(alias="UniqaClaimID_ToXml")
    ClaimStatus: ClaimStatusOutput
    ClaimStatusComment: Optional[str] = None

    class Config:
        populate_by_name = True
