from flask import Flask, request, Response

app = Flask(__name__)

@app.route('/soap', methods=['POST'])
def soap_service():
    # Extract the SOAP request
    soap_request = request.data

    # For demonstration, we'll just return a static SOAP response
    soap_response = """<?xml version="1.0" encoding="UTF-8"?>
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
       <soapenv:Body>
          <sayHelloResponse>
             <greeting>Hello, World!</greeting>
          </sayHelloResponse>
       </soapenv:Body>
    </soapenv:Envelope>"""

    return Response(soap_response, mimetype='text/xml')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)