# SOAP Web Service Implementation

This project implements a SOAP web service that provides insurance-related functionality through a secure SSL channel with Triple DES encrypted XML payloads.

## Overview

The SOAP web service exposes six separate methods, each requiring authentication:

1. **SendRegistration** - Create a new insurance policy
2. **GetStatus** - Check the status of an existing policy
3. **Storno** - Cancel an existing policy
4. **ChangeRegistration** - Update information for an existing policy
5. **SendClaim** - Submit a new insurance claim
6. **GetClaimStatus** - Check the status of a claim

## Security Features

- **Triple DES Encryption**: All XML data is encrypted using Triple DES (ECB mode with PKCS7 padding)
- **Authentication**: Username/password authentication for all requests
- **SSL Support**: Optional secure communication channel
- **Test/Live Modes**: Separate environments for testing and production

## Project Structure

```
soap-web-services/
├── server/
│   ├── app.py                # Main SOAP server application
│   ├── config.py             # Configuration settings
│   ├── test_client.py        # Test client for all request types
│   ├── models/               # Data models
│   ├── security/             # Authentication and encryption
│   ├── services/             # SOAP service implementations
│   ├── storage/              # Data repositories
│   └── utils/                # Utility functions
```

## Requirements

- Python 3.7+
- Required packages:
  - spyne (SOAP framework)
  - pycryptodome (Triple DES encryption)
  - lxml (XML processing)
  - python-dotenv (configuration)
  - requests (HTTP client for testing)

## Configuration

Configure the `.env` file in the server directory:

```
SECRET_KEY=your-secret-key-here     # Used for Triple DES encryption
SERVICE_USER=admin                  # Username for authentication
SERVICE_PASSWORD=securepassword     # Password for authentication
SYSTEM_MODE=TEST                    # TEST or LIVE
SSL_CERT_PATH=/path/to/cert.pem     # Optional, for HTTPS
SSL_KEY_PATH=/path/to/key.pem       # Optional, for HTTPS
```

## Running the Server

```bash
cd soap-web-services/server
python app.py
```

The server will start on http://0.0.0.0:8000 by default (or https if SSL is configured).

## Testing the Service

The project includes two different test clients:

1. A test client for separate SOAP methods:
```bash
cd soap-web-services/server
python test_separate_methods.py
```

2. A test client that follows the initial specification:
```bash
cd soap-web-services/server
python test_client.py
```

Both clients will test:
1. Authentication
2. SendRegistration
3. GetStatus
4. ChangeRegistration
5. SendClaim
6. GetClaimStatus
7. Storno

## Message Structure

### Separate Methods Approach

**Example Request (SendRegistration):**
```xml
<soapenv:Envelope>
   <soapenv:Body>
      <SendRegistration>
         <username>admin</username>
         <password>securepassword</password>
         <xml_data>EncryptedXMLData</xml_data>
      </SendRegistration>
   </soapenv:Body>
</soapenv:Envelope>
```

**Example Response (SendRegistration):**
```xml
<soapenv:Envelope>
   <soapenv:Body>
      <SendRegistrationResponse>
         <return>EncryptedXMLData</return>
      </SendRegistrationResponse>
   </soapenv:Body>
</soapenv:Envelope>
```

### Response Formats

- Success responses are encrypted XML containing the appropriate data for each operation
- Error responses are encrypted XML containing an `<e>` tag with the error message

### Error Handling

Possible error messages include:
- Authentication failed
- Invalid Secret key
- Invalid XML
- Registration failed
- Policy not found
- Claim not found
- Other operation-specific errors

## Integration Guide

To integrate with this service:

1. Create an HTTP client capable of sending SOAP requests
2. Implement Triple DES encryption for XML data using the MD5 hash of the key
3. Send properly formatted SOAP requests to the specific method endpoints
4. Include authentication credentials with every request
5. Decrypt and process the response

For detailed implementation examples, refer to:
- `test_separate_methods.py` - For separate method calls
- `test_client.py` - For the original specification

## Test and Live Environments

The service can operate in two modes:
- **TEST** mode: For testing integration without affecting production data
- **LIVE** mode: For production use with real data

These are configured via the `SYSTEM_MODE` environment variable.