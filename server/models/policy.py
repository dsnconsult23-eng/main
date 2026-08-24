# models/policy.py
from pydantic import BaseModel, field_validator
from lxml import etree as ET
from typing import Optional

class GetStatusInputData(BaseModel):
    GACID: str
    UniqaOfferID: Optional[str] = None
    
# models/policy.py
from pydantic import BaseModel, field_validator
from lxml import etree as ET
from typing import Optional

class GetStatusInputData(BaseModel):
    GACID: str
    UniqaOfferID: Optional[str] = None
    
    @classmethod
    def from_xml_element(cls, element: ET._Element):
        return cls(
            GACID=element.findtext("GACID"),
            UniqaOfferID=element.findtext("UniqaOfferID")
        )

class GetStatusOutputData(BaseModel):
    def from_xml_element(cls, element: ET._Element):
        return cls(
            GACID=element.findtext("GACID"),
            UniqaOfferID=element.findtext("UniqaOfferID")
        )

class GetStatusOutputData(BaseModel):
    GACID: str
    UniqaOfferID: str
    PolicyNumber: Optional[str] = None  # Empty if status 1 or 3
    PolicyStatus: str  # 1=Waiting, 2=Issued, 3=Rejected, 4=Storno, 5=Cancelled
    PolicyStatusComment: Optional[str] = None
    
    @field_validator('PolicyStatus')
    def validate_status(cls, v):
        if v not in {'-1', '1', '2', '3', '4', '5'}:
            raise ValueError('PolicyStatus must be 1-5')
        return v
    
    def to_xml_element(self, root_tag_name_override: str = None) -> ET._Element:
        root = ET.Element(root_tag_name_override or "GetStatusOutput")
        ET.SubElement(root, "GACID").text = self.GACID
        ET.SubElement(root, "UniqaOfferID").text = self.UniqaOfferID
        
        if self.PolicyNumber is not None:
            ET.SubElement(root, "PolicyNumber").text = self.PolicyNumber
        
        ET.SubElement(root, "PolicyStatus").text = self.PolicyStatus
        
        if self.PolicyStatusComment is not None:
            ET.SubElement(root, "PolicyStatusComment").text = self.PolicyStatusComment
            
        return root