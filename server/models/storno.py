# models/storno.py
from pydantic import BaseModel, field_validator
from lxml import etree as ET
from typing import Optional, Literal
from datetime import datetime

class StornoInputData(BaseModel):
    GACID: str
    PolicyNumber: str
    Type: Literal["Storno", "Cancellation"]
    RequestDate: Optional[str] = None
    
    @field_validator('RequestDate')
    def validate_request_date(cls, v):
        if v:
            try:
                datetime.strptime(v, "%d-%m-%Y")
            except ValueError:
                raise ValueError("RequestDate must be in DD-MM-YYYY format")
        return v
    
    @classmethod
    def from_xml_element(cls, element: ET._Element):
        return cls(
            GACID=element.findtext("GACID"),
            PolicyNumber=element.findtext("PolicyNumber"),
            Type=element.findtext("Type"),
            RequestDate=element.findtext("RequestDate")
        )

class StornoOutputData(BaseModel):
    GACID: str
    PolicyNumber: str
    RiskEndDate: str  # DD-MM-YYYY format
    PolicyStatus: Literal["1", "2", "3", "4", "5"]
    
    @field_validator('RiskEndDate')
    def validate_risk_end_date(cls, v):
        for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(v, fmt)
                return parsed.strftime("%d-%m-%Y")  # Normalize to DD-MM-YYYY
            except ValueError:
                continue
        raise ValueError("RiskEndDate must be in DD-MM-YYYY format")
    
    def to_xml_element(self, root_tag_name_override: str = None) -> ET._Element:
        root = ET.Element(root_tag_name_override or "StornoOutput")
        ET.SubElement(root, "GACID").text = self.GACID
        ET.SubElement(root, "PolicyNumber").text = self.PolicyNumber
        ET.SubElement(root, "RiskEndDate").text = self.RiskEndDate
        ET.SubElement(root, "PolicyStatus").text = self.PolicyStatus
        return root