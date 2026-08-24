from spyne import ServiceBase, rpc, Unicode
from spyne import ServiceBase, rpc, Unicode
from lxml import etree
from security.encryption import DataSecurity
from security.encryption import DataSecurity
from security.authentication import Authenticator
from models.policy import GetStatusInputData, GetStatusOutputData
from models.policy import GetStatusInputData, GetStatusOutputData
from models.storno import StornoInputData, StornoOutputData
from models.change_registration import ChangeRegistrationInputData, ChangeRegistrationOutputData
from models.claim import SendClaimInputData, SendClaimOutputData, GetClaimStatusInputData, GetClaimStatusOutputData
from models.send_documents import SendDocumentsInputData, SendDocumentsOutputData
from config import Config
from db.database import connect_informix, connect_informix_storno,insert_polisa_sertifikati, call_generiraj_polisa_sertifikati, call_generiraj_polisa_sertifikati_status, insert_claim_data, call_generiraj_polisa_sertifikati_canceled, call_generiraj_polisa_claim, call_generiraj_polisa_claim_status, save_registration_documents, save_claim_documents, save_policy_documents
import logging
from utils.parse_registration import parse_registration_xml

logger = logging.getLogger(__name__)

class InsuranceSoapService(ServiceBase):
    def __init__(self):
        self.data_security = DataSecurity()
    def __init__(self):
        self.data_security = DataSecurity()
        self.authenticator = Authenticator()

    @rpc(Unicode, Unicode, Unicode, Unicode, _returns=Unicode)
    def SendRequest(ctx, UserName, Password, RequestType, XMLData):
        service = ctx.descriptor.service_class()
        logger.info(f"Received {RequestType} request from {UserName}")

        try:
            # 1. Authentication
            if not service.authenticator.authenticate(UserName, Password):
                return service._format_error(RequestType, "Authentication failed")

            # 2. Decryption
            decrypted_xml = service.data_security.decrypt_xml(XMLData)
            logger.info(
                "Full decrypted XML payload for %s from %s:\n%s",
                RequestType,
                UserName,
                decrypted_xml,
            )
            if not decrypted_xml.strip():
                return service._format_error(RequestType, "Empty XML payload")

            # 3. Parse XML
            root = etree.fromstring(decrypted_xml.encode('utf-8'))

            # 4. Route request - ADD ALL HANDLERS HERE
            handler_mapping = {
                "SendRegistration": service._handle_send_registration,
                "GetStatus": service._handle_get_status,
                "Storno": service._handle_storno,
                "ChangeRegistration": service._handle_change_registration,
                "SendClaim": service._handle_send_claim,
                "GetClaimStatus": service._handle_get_claim_status,
                "sendDocuments": service._handle_send_documents,
                # Add other request types as needed...
            }
            
            handler = handler_mapping.get(RequestType)
            if not handler:
                return service._format_error(RequestType, "Invalid RequestType")
            
            response = handler(root)

            # 5. Encrypt response
            encrypted_response = service.data_security.encrypt_xml(response)
            return service._format_success(RequestType, encrypted_response)

        except Exception as e:
            logger.error(f"Error processing request: {str(e)}", exc_info=True)
            return service._format_error(RequestType, str(e))

    def _format_error(self, request_type, message):
        return f"""<root>
            <Status>0</Status>
            <Error>{message}</Error>
            <RequestType>{request_type}</RequestType>
            <XMLResult></XMLResult>
        </root>"""

    def _format_success(self, request_type, xml_result):
        return f"""<root>
            <Status>1</Status>
            <Error></Error>
            <RequestType>{request_type}</RequestType>
            <XMLResult>{xml_result}</XMLResult>
        </root>"""

    def _create_error_payload_xml_str(self, message: str) -> str:
        root = etree.Element("root")
        etree.SubElement(root, "Error").text = message or ""
        return etree.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")

    def _handle_send_registration(self, xml_root):
        # Implement your handler logic here
        xml_data = parse_registration_xml(xml_root)
        gacid = xml_root.findtext("GACID")
        result = None
        logger.debug(f"[SendRegistration] Parsed XML data: {xml_data}")

        try:
            conn, cursor, success = connect_informix()
            
            insert_polisa_sertifikati(xml_data, cursor, conn)
            conn.commit()
            cursor.close()
            conn.close()    
            conn1, cursor1, success1 = connect_informix()
            result = call_generiraj_polisa_sertifikati(cursor1, 1, xml_data['CertificateID'])
            policy_number = result[2] if result and len(result) > 2 else None
            if policy_number and xml_data.get("Documents"):
                save_registration_documents(xml_data, str(policy_number), cursor1, conn1)
            conn1.commit()
            cursor1.close()
            conn1.close()
        except Exception as e:
            logger.error(f"[SendRegistration] Database connection error: {str(e)}", exc_info=True)
            return self._format_error("SendRegistration", "Database connection failed")
        finally:
            pass
        if result[0] == -1:
            return f"""
            <root>
            <Error>{result[4]}</Error>
            </root>"""
        elif result[0] == 1 and result[3] != 3:
            return f"""<root>
                        <GACID>{gacid}</GACID>
                        <UniqaOfferID>{result[1]}</UniqaOfferID>
                        <PolicyNumber>{result[2]}</PolicyNumber>
                        <PolicyStatus>{result[3]}</PolicyStatus>
                        </root>"""
        else:
            return f"""<root>
                        <GACID>{gacid}</GACID>
                        <UniqaOfferID>{result[1]}</UniqaOfferID>
                     
                        <PolicyNumber>{result[2]}</PolicyNumber>
                        <PolicyStatus>{result[3]}</PolicyStatus>
                        
                        <PolicyStatusComment>{result[4]}</PolicyStatusComment>
                        </root>"""
    
    def _handle_get_status(self, xml_input_root: etree._Element) -> str:
        """Handle GetStatus requests according to exact specifications"""
        try:
            conn, cursor, success = connect_informix()
            if not success or conn is None or cursor is None:
                raise RuntimeError("Database connection failed before inserting claim data")
            input_data = GetStatusInputData.from_xml_element(xml_input_root)
            logger.debug(f"[GetStatus] Input data: {input_data.model_dump_json()}")
            
            # Validate GACID format (mock validation)
            if not input_data.GACID.startswith("PPIMK"):
                error_xml = """<?xml version='1.0' encoding='utf-8'?>
                    <root>
                        <Error>Invalid GACID!</Error>
                    </root>"""
                return error_xml
            result = call_generiraj_polisa_sertifikati_status(cursor, input_data.UniqaOfferID)
            # Mock database lookup - replace with actual database call
            policy_data = {
                "GACID": input_data.GACID,
                "UniqaOfferID": input_data.UniqaOfferID or f"OFF_{input_data.GACID.split('/')[0]}",
                "PolicyNumber": str(result['policy_number']),  # Mock policy number - replace with real lookup
                "PolicyStatus": str(result['policy_status']),  # Mock status - replace with real lookup
                "PolicyStatusComment": result.get('policy_status_comment', None),  # Optional comment
            }
            
            # Create response
            response_model = GetStatusOutputData(**policy_data)
            
            return etree.tostring(
                response_model.to_xml_element(root_tag_name_override="root"),
                encoding='utf-8',
                xml_declaration=True
            ).decode('utf-8')
            
        except Exception as e:
            logger.error(f"[GetStatus] Error: {str(e)}", exc_info=True)
            return self._create_error_payload_xml_str(f"Error processing GetStatus: {str(e)}")
        
    def _handle_storno(self, xml_input_root: etree._Element) -> str:
        """Handle Storno/Cancellation requests according to specifications"""
        try:
            input_data = StornoInputData.from_xml_element(xml_input_root)
            logger.debug(f"[Storno] Input data: {input_data.model_dump_json()}")

            conn, cursor, success = connect_informix_storno()
            result = call_generiraj_polisa_sertifikati_canceled(cursor, input_data.GACID, input_data.PolicyNumber ,input_data.Type, input_data.RequestDate)
        
            conn.close()
            cursor.close()  
            
            # Validate input
            if not input_data.GACID.startswith("PPIMK"):
                error_xml = """<?xml version='1.0' encoding='utf-8'?>
                    <root>
                        <Error>Invalid GACID!</Error>
                    </root>"""
                return error_xml
            
            if input_data.Type == "Cancellation" and not input_data.RequestDate:
                raise ValueError("RequestDate is required for Cancellation")
            
            if result['result'][0] == -1:
                return f"""<root>
                    <Error>{result['result'][5]}</Error>
                </root>"""
            
            # Mock processing - replace with actual business logic
            risk_end_date = (
                result['result'][3]   # Default for Storno
                if input_data.Type == "Storno"
                else input_data.RequestDate
            )
            
            # Create response
            response_model = StornoOutputData(
                GACID=input_data.GACID,
                PolicyNumber=input_data.PolicyNumber,
                RiskEndDate=result['result'][3] if input_data.Type == "Storno" else input_data.RequestDate,
                UniqaOfferID=f"OFF_{input_data.GACID.split('/')[0]}",
                PolicyStatus="4" if input_data.Type == "Storno" else "5"
            )
            
            return etree.tostring(
                response_model.to_xml_element(root_tag_name_override="root"),
                encoding='utf-8',
                xml_declaration=True
            ).decode('utf-8')
            
        except ValueError as ve:
            logger.error(f"[Storno] Validation error: {str(ve)}", exc_info=True)
            return self._create_error_payload_xml_str(str(ve))
        except Exception as e:
            logger.error(f"[Storno] Processing error: {str(e)}", exc_info=True)
            return self._create_error_payload_xml_str(f"Error processing Storno: {str(e)}")
    
    def _handle_change_registration(self, xml_input_root: etree._Element) -> str:
        """Handle ChangeRegistration requests according to specifications"""
        try:
            print(xml_input_root)
            input_data = ChangeRegistrationInputData.from_xml_element(xml_input_root)
            logger.debug(f"[ChangeRegistration] Input data: {input_data.model_dump_json()}")
            conn, cursor, success = connect_informix()
            insert_policy_certificate(input_data.model_dump_json())
            call_generiraj_polisa_sertifikati(cursor, 2, input_data.GACID)
            conn.close()
            cursor.close()
            
            # Validate GACID format
            if not input_data.GACID.startswith("PPIMK"):
                error_xml = """<?xml version='1.0' encoding='utf-8'?>
                    <root>
                        <Error>Invalid GACID!</Error>
                    </root>"""
                return error_xml
            
            # Mock processing - replace with actual business logic
            # Here you would typically:
            # 1. Validate the policy exists
            # 2. Update the insured data in your database
            # 3. Return success response
            
            # Create response
            response_model = ChangeRegistrationOutputData(
                GACID=input_data.GACID,
                PolicyNumber=input_data.PolicyNumber
            )
            
            return etree.tostring(
                response_model.to_xml_element(root_tag_name_override="root"),
                encoding='utf-8',
                xml_declaration=True
            ).decode('utf-8')
            
        except ValueError as ve:
            logger.error(f"[ChangeRegistration] Validation error: {str(ve)}", exc_info=True)
            return self._create_error_payload_xml_str(str(ve))
        except Exception as e:
            logger.error(f"[ChangeRegistration] Processing error: {str(e)}", exc_info=True)
            return self._create_error_payload_xml_str(f"Error processing ChangeRegistration: {str(e)}")
    
    def _handle_send_claim(self, xml_input_root: etree._Element) -> str:
        """Handle SendClaim requests according to specifications"""
        try:
            input_data = SendClaimInputData.from_xml_element(xml_input_root)
            logger.debug(f"[SendClaim] Input data: {input_data.model_dump_json()}")
            conn, cursor, success = connect_informix()

            insert_claim_data(input_data.model_dump_json(), cursor, conn)
            conn.commit()
            cursor.close()
            conn.close()
            conn, cursor, success = connect_informix()
            if not success or conn is None or cursor is None:
                raise RuntimeError("Database connection failed before generating claim number")

            result = call_generiraj_polisa_claim(cursor, input_data.GACID, 1, 6)

            claim_result = result.get('result') if result else None
            generated_policy_number = claim_result[2] if claim_result and len(claim_result) > 2 else input_data.PolicyNumber
            generated_claim_id = claim_result[-1] if claim_result else None
            if generated_claim_id and input_data.ReportClaim.Documents:
                save_claim_documents(input_data.model_dump(), str(generated_policy_number),
                                     str(generated_claim_id), cursor, conn)

            conn.commit()
            cursor.close()
            conn.close()
            # Validate GACID format
            if not input_data.GACID.startswith("PPIMK"):
                error_xml = """<?xml version='1.0' encoding='utf-8'?>
                    <root>
                        <Error>Invalid GACID!</Error>
                    </root>"""
                return error_xml

            # Mock processing - replace with actual business logic
            # Here you would typically:
            # 1. Validate the policy exists
            # 2. Store the claim data in your database
            # 3. Process any attached documents
            # 4. Generate a claim reference
            
            # Create response
            response_model = SendClaimOutputData(
                GACID=result['result'][1],
                PolicyNumber=result['result'][2],
                UniqaClaimID=result['result'][-1]
            )
            
            return etree.tostring(
                response_model.to_xml_element(),
                encoding='utf-8',
                xml_declaration=True
            ).decode('utf-8')
            
        except ValueError as ve:
            logger.error(f"[SendClaim] Validation error: {str(ve)}", exc_info=True)
            return self._create_error_payload_xml_str(str(ve))
        except Exception as e:
            logger.error(f"[SendClaim] Processing error: {str(e)}", exc_info=True)
            return self._create_error_payload_xml_str(f"Error processing claim: {str(e)}")

    def _handle_send_documents(self, xml_input_root: etree._Element) -> str:
        """Handle sendDocuments requests for existing policies."""
        conn = cursor = None
        try:
            input_data = SendDocumentsInputData.from_xml_element(xml_input_root)
            if not input_data.Policy:
                return self._format_error("sendDocuments", "Policy is required")
            if not input_data.Documents:
                return self._format_error("sendDocuments", "At least one document is required")

            conn, cursor, success = connect_informix()
            if not success or conn is None or cursor is None:
                return self._format_error("sendDocuments", "Database connection failed")

            save_policy_documents(input_data.Policy, input_data.Documents, cursor, conn)
            response = SendDocumentsOutputData(
                Policy=input_data.Policy,
                DocumentsCount=len(input_data.Documents),
            )
            return etree.tostring(response.to_xml_element(), encoding='utf-8',
                                  xml_declaration=True).decode('utf-8')
        except ValueError as exc:
            logger.error("[sendDocuments] Validation error: %s", exc, exc_info=True)
            return self._format_error("sendDocuments", str(exc))
        except Exception as exc:
            if conn is not None:
                conn.rollback()
            logger.error("[sendDocuments] Processing error: %s", exc, exc_info=True)
            return self._format_error("sendDocuments", f"Error processing sendDocuments: {exc}")
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
      
    def _handle_get_claim_status(self, xml_input_root: etree._Element) -> str:
        """Handle GetClaimStatus requests according to specifications"""
        try:
            input_data = GetClaimStatusInputData.from_xml_element(xml_input_root)
            logger.debug(f"[GetClaimStatus] Input data: {input_data.model_dump_json()}")
            conn, cursor, success = connect_informix()

            call_generiraj_polisa_claim_status(cursor, input_data.GACClaimID, input_data.PolicyNumber, input_data.UniqaClaimID, 6)
            cursor.close()
            conn.close()
            # Validate GACClaimID format
            if not input_data.GACClaimID.startswith("PPIMKC"):
                error_xml = """<?xml version='1.0' encoding='utf-8'?>
                    <root>
                        <Error>Invalid GACClaimID!</Error>
                    </root>"""
                return error_xml
            
            # Mock database lookup - replace with actual database call
            # Here you would typically:
            # 1. Query your database for the claim status
            # 2. Return the current status and optional comment
            claim_status_data = {
                "GACClaimID": input_data.GACClaimID,
                "PolicyNumber": input_data.PolicyNumber,
                "UniqaClaimID": input_data.UniqaClaimID,
                "ClaimStatus": "1",  # Mock status - replace with real lookup
                "ClaimStatusComment": None  # Add comment if status is rejected (3)
            }
            
            # Create response
            response_model = GetClaimStatusOutputData(**claim_status_data)
            
            return etree.tostring(
                response_model.to_xml_element(root_tag_name_override="root"),
                encoding='utf-8',
                xml_declaration=True
            ).decode('utf-8')
            
        except Exception as e:
            logger.error(f"[GetClaimStatus] Error: {str(e)}", exc_info=True)
            return self._create_error_payload_xml_str(f"Error processing claim status: {str(e)}")
            logger.error(f"[GetClaimStatus] Error: {str(e)}", exc_info=True)
            return self._create_error_payload_xml_str(f"Error processing claim status: {str(e)}")
