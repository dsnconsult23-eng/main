from zeep import Client
from zeep.transports import Transport
from requests import Session

WSDL = "https://your-test-url?wsdl"

session = Session()
session.verify = True
transport = Transport(session=session)
client = Client(wsdl=WSDL, transport=transport)

def send_request(username, password, request_type, encrypted_xml):
    result = client.service.SendRequest(
        UserName=username,
        Password=password,
        RequestType=request_type,
        XMLData=encrypted_xml
    )
    return {
        "Status": result.Status,
        "Error": result.Error,
        "RequestType": result.RequestType,
        "XMLResult": result.XMLResult
    }
