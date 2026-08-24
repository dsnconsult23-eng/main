# models/change_registration.py
from pydantic import BaseModel, field_validator
from lxml import etree as ET
from typing import Optional
from datetime import datetime

class InsuredData(BaseModel):
    PartnerReferenceID: str
    PersonType: str  # "1"=Individual, "0"=Company
    VATNumber: Optional[str] = None
    Title: Optional[str] = None
    LastName: str
    FirstName: str
    Country: str  # ISO 3166-1 alpha-2
    ZIP: str
    State: str
    City: str
    Street: str
    BirthPlace: str
    BirthDateDMY: str  # DD-MM-YYYY
    Gender: Optional[str] = None  # "Male" or "Female"
    Phone: str
    Email: str

    @field_validator('BirthDateDMY')
    def validate_birth_date(cls, v):
        try:
            datetime.strptime(v, "%d-%m-%Y")
        except ValueError:
            raise ValueError("BirthDateDMY must be in DD-MM-YYYY format")
        return v

    @field_validator('PersonType')
    def validate_person_type(cls, v):
        if v not in {"0", "1"}:
            raise ValueError("PersonType must be 0 (Company) or 1 (Individual)")
        return v

    @classmethod
    def from_xml_element(cls, element: ET._Element):
        return cls(
            PartnerReferenceID=element.findtext("PartnerReferenceID"),
            PersonType=element.findtext("PersonType"),
            VATNumber=element.findtext("VATNumber"),
            Title=element.findtext("Title"),
            LastName=element.findtext("LastName"),
            FirstName=element.findtext("FirstName"),
            Country=element.findtext("Country"),
            ZIP=element.findtext("ZIP"),
            State=element.findtext("State"),
            City=element.findtext("City"),
            Street=element.findtext("Street"),
            BirthPlace=element.findtext("BirthPlace"),
            BirthDateDMY=element.findtext("BirthDateDMY"),
            Gender=element.findtext("Gender"),
            Phone=element.findtext("Phone"),
            Email=element.findtext("Email")
        )

class ChangeRegistrationInputData(BaseModel):
    GACID: str
    PolicyNumber: str
    Insured: InsuredData
    
    @classmethod
    def from_xml_element(cls, element: ET._Element):
        insured_element = element.find("Insured")
        if insured_element is None:
            raise ValueError("Insured element is required")
        
        return cls(
            GACID=element.findtext("GACID"),
            PolicyNumber=element.findtext("PolicyNumber"),
            Insured=InsuredData.from_xml_element(insured_element)
        )

class ChangeRegistrationOutputData(BaseModel):
    GACID: str
    PolicyNumber: str
    
    def to_xml_element(self, root_tag_name_override: str = None) -> ET._Element:
        root = ET.Element(root_tag_name_override or "ChangeRegistrationOutput")
        ET.SubElement(root, "GACID").text = self.GACID
        ET.SubElement(root, "PolicyNumber").text = self.PolicyNumber
        return root