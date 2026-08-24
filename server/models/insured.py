# soap-web-services/server/models/insured.py
from pydantic import Field
from typing import Optional

from .base_model import BaseXmlModel # <--- Ensure BaseXmlModel is imported

# Ensure Insured inherits from BaseXmlModel
class Insured(BaseXmlModel):
    PartnerReferenceID: str
    PersonType: str
    VATNumber: Optional[str] = Field(default=None)
    Title: Optional[str] = Field(default=None)
    LastName: str
    FirstName: str
    Country: str
    ZIP: str
    State: Optional[str] = Field(default=None)
    City: str
    Street: str
    BirthPlace: str
    BirthDateDMY: str
    Gender: str
    Phone: Optional[str] = Field(default=None)
    Email: Optional[str] = Field(default=None)

    class Config:
        populate_by_name = True