# soap-web-services/server/models/soap_responses.py
from __future__ import annotations # VERY FIRST LINE

from spyne import ComplexModel, Unicode

class SendRequestOutput(ComplexModel):
    """
    Defines the structure for the output of the SendRequest SOAP method,
    matching the four return values specified in the PDF.
    """
    # __namespace__ = 'tns' # Optional: if you want to control namespace for this type specifically
    # _type_name = "OutputData" # Optional: to control the complex type name in WSDL schema

    Status: Unicode(min_occurs=1, nillable=False, documentation="Result code of the request ('0' for error, '1' for success).")
    Error: Unicode(min_occurs=0, nillable=True, documentation="Error message(s) of the response, if Status is '0'.")
    RequestTypeOut: Unicode(min_occurs=1, nillable=False, documentation="Echoes the type of the request processed.")
    XMLResult: Unicode(min_occurs=0, nillable=True, documentation="Detailed data of the response, Triple DES encrypted XML string.")

    # You can add ordering if specific XML element order is critical, though usually not necessary
    # _ordered = True
    # _in_sequence = ['Status', 'Error', 'RequestTypeOut', 'XMLResult']

