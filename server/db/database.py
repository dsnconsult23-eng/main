import os
import platform
import logging
import base64
import binascii
import re
import textwrap
from pathlib import Path
from email import policy
from email.parser import BytesParser
import jaydebeapi
from datetime import datetime
from jaydebeapi import DatabaseError
import json
import uuid
from typing import Union, Dict, Any
from config import Config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _sanitize_path_part(value: str, default: str) -> str:
    raw = (value or '').strip()
    if not raw:
        return default
    sanitized = ''.join(ch if ch.isalnum() or ch in ('-', '_', '.') else '_' for ch in raw)
    return sanitized or default


def _decode_document(document_base64: str, index: int) -> bytes:
    try:
        return base64.b64decode(document_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"Invalid base64 document at position {index}") from exc


def _detect_document_extension(document_bytes: bytes) -> str:
    """Return an extension matching the actual payload, not its XML tag."""
    header = document_bytes[:2048].lstrip()
    if header.startswith(b'%PDF'):
        return '.pdf'
    if header.startswith(b'\xff\xd8\xff'):
        return '.jpg'
    if header.startswith(b'\x89PNG\r\n\x1a\n'):
        return '.png'
    if header.startswith((b'GIF87a', b'GIF89a')):
        return '.gif'
    if header.startswith((b'II*\x00', b'MM\x00*')):
        return '.tif'
    return '.bin'


def save_registration_documents(registration_data: dict, policy_number: str, cursor: Any, conn: Any) -> bool:
    """Save documents supplied with SendRegistration."""
    documents = registration_data.get('Documents') or []
    if not documents:
        return True

    safe_policy = _sanitize_path_part(policy_number, "UNKNOWN_POLICY")
    base_dir = Path(Config.DOCUMENT_STORAGE_PATH) / safe_policy
    base_dir.mkdir(parents=True, exist_ok=True)
    sql = f"""INSERT INTO {Config.DOCUMENTS_TABLE}
        (policy_number, gacid, certificate_id, document_name, file_path, document_base64, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)"""

    for index, encoded in enumerate(documents, start=1):
        if not encoded or not str(encoded).strip():
            continue
        data = _decode_document(encoded, index)
        name = f"{safe_policy}_{index:03d}{_detect_document_extension(data)}"
        file_path = base_dir / name
        file_path.write_bytes(data)
        cursor.execute(sql, (policy_number, registration_data.get('GACID', ''),
                       registration_data.get('CertificateID', ''), name, str(file_path),
                       encoded, format_datetime(datetime.now())))
    conn.commit()
    return True


def save_policy_documents(policy_number: str, documents: list[str], cursor: Any, conn: Any) -> bool:
    """Save additional documents for an existing policy."""
    if cursor is None or conn is None:
        raise ValueError("Database connection is not available")
    if not documents:
        return True

    safe_policy = _sanitize_path_part(policy_number, "UNKNOWN_POLICY")
    base_dir = Path(Config.DOCUMENT_STORAGE_PATH) / safe_policy
    base_dir.mkdir(parents=True, exist_ok=True)
    sql = f"""INSERT INTO {Config.DOCUMENTS_TABLE}
        (policy_number, gacid, certificate_id, document_name, file_path, document_base64, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)"""

    # A policy may receive documents in multiple sendDocuments calls. Include a
    # request identifier so a later call cannot overwrite files from an earlier
    # call that also starts at index 1.
    request_id = datetime.now().strftime('%Y%m%dT%H%M%S%f') + '_' + uuid.uuid4().hex[:8]
    for index, encoded in enumerate(documents, start=1):
        if not encoded or not str(encoded).strip():
            continue
        data = _decode_document(encoded, index)
        extension = _detect_document_extension(data)
        name = f"{safe_policy}_extra_{request_id}_{index:03d}{extension}"
        file_path = base_dir / name
        file_path.write_bytes(data)
        cursor.execute(sql, (policy_number, '', '', name, str(file_path), encoded,
                       format_datetime(datetime.now())))
    conn.commit()
    return True


def save_claim_documents(claim_data: dict, policy_number: str, uniqa_claim_id: str,
                         cursor: Any, conn: Any) -> bool:
    """Save claim documents, converting EML payloads to PDF on the server."""
    documents = (claim_data.get('ReportClaim') or {}).get('Documents') or []
    if not documents:
        return True

    safe_claim = _sanitize_path_part(uniqa_claim_id, "UNKNOWN_CLAIM")
    safe_policy = _sanitize_path_part(policy_number, "UNKNOWN_POLICY")
    base_dir = Path(Config.CLAIM_DOCUMENT_STORAGE_PATH) / safe_policy / safe_claim
    base_dir.mkdir(parents=True, exist_ok=True)
    sql = f"""INSERT INTO {Config.CLAIM_DOCUMENTS_TABLE}
        (uniqa_claim_id, policy_number, gacid, document_name, file_path, document_base64, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)"""

    for index, encoded in enumerate(documents, start=1):
        if not encoded or not str(encoded).strip():
            continue
        data = _decode_document(encoded, index)
        extension = _detect_claim_document_extension(data)
        if extension == '.eml':
            data = _convert_eml_to_pdf_bytes(data)
            extension = '.pdf'
        name = f"{safe_claim}_{index:03d}{extension}"
        file_path = base_dir / name
        file_path.write_bytes(data)
        cursor.execute(sql, (uniqa_claim_id, policy_number, claim_data.get('GACID', ''),
                       name, str(file_path), encoded, format_datetime(datetime.now())))
    conn.commit()
    return True


def _detect_claim_document_extension(document_bytes: bytes) -> str:
    extension = _detect_document_extension(document_bytes)
    if extension != '.bin':
        return extension
    header = document_bytes[:2048].lstrip()
    markers = (b'from:', b'to:', b'subject:', b'mime-version:', b'content-type:', b'received:')
    if any(marker in header.lower() for marker in markers):
        return '.eml'
    return '.bin'


def _convert_eml_to_pdf_bytes(eml_bytes: bytes) -> bytes:
    message = BytesParser(policy=policy.default).parsebytes(eml_bytes)
    body_part = message.get_body(preferencelist=('plain', 'html'))
    body = body_part.get_content() if body_part is not None else ''
    if body_part is not None and body_part.get_content_type() == 'text/html':
        body = re.sub(r'(?is)<(script|style).*?</\\1>', '', body)
        body = re.sub(r'(?s)<[^>]+>', ' ', body)
        body = re.sub(r'\s+', ' ', body)
    attachments = [part.get_filename() for part in message.iter_attachments() if part.get_filename()]
    lines = ['Email message', '', f"From: {message.get('from', '')}",
             f"To: {message.get('to', '')}", f"Cc: {message.get('cc', '')}",
             f"Date: {message.get('date', '')}", f"Subject: {message.get('subject', '')}"]
    if attachments:
        lines.append(f"Attachments: {', '.join(attachments)}")
    lines.extend(['', body or ''])
    return _build_text_pdf('\n'.join(lines))


def _build_text_pdf(text: str) -> bytes:
    wrapped = []
    for raw_line in text.splitlines():
        wrapped.extend(textwrap.wrap(raw_line, width=95) or [''])
    pages = [wrapped[i:i + 54] for i in range(0, len(wrapped), 54)] or [['']]
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>']
    page_ids = [3 + i * 2 for i in range(len(pages))]
    kids = b' '.join(f'{object_id} 0 R'.encode('ascii') for object_id in page_ids)
    objects.append(b'<< /Type /Pages /Kids [' + kids + b'] /Count ' + str(len(pages)).encode() + b' >>')
    font_id = 3 + len(pages) * 2
    for page_index, lines in enumerate(pages):
        page_id = 3 + page_index * 2
        content_id = page_id + 1
        stream_lines = ['BT', '/F1 10 Tf', '50 750 Td', '14 TL']
        for line in lines:
            escaped = line.encode('latin-1', errors='replace').decode('latin-1')
            escaped = escaped.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
            stream_lines.extend([f'({escaped}) Tj', 'T*'])
        stream_lines.append('ET')
        content = '\n'.join(stream_lines).encode('latin-1')
        objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>'.encode())
        objects.append(b'<< /Length ' + str(len(content)).encode() + b' >>\nstream\n' + content + b'\nendstream')
    objects.append(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
    pdf = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for index, content in enumerate(objects, start=1):
        offsets.append(len(pdf)); pdf.extend(f'{index} 0 obj\n'.encode()); pdf.extend(content); pdf.extend(b'\nendobj\n')
    xref = len(pdf)
    pdf.extend(f'xref\n0 {len(objects) + 1}\n'.encode()); pdf.extend(b'0000000000 65535 f \n')
    for offset in offsets[1:]:
        pdf.extend(f'{offset:010d} 00000 n \n'.encode())
    pdf.extend(f'trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    return bytes(pdf)

def set_java_home():
    """Set JAVA_HOME environment variable"""
    # java_home_path = r"C:\Users\supportuniqalife\AppData\Local\Programs\Eclipse Adoptium\jdk-21.0.7.6-hotspot"
    java_home_path = r"/usr/lib/jvm/java-11-openjdk-11.0.25.0.9-7.el9.x86_64"  # Example for Linux, adjust as needed
    os.environ["JAVA_HOME"] = java_home_path
    logger.info(f"JAVA_HOME set to: {java_home_path}")

def get_informix_drivers():
    """Locate and validate Informix JDBC drivers"""
    if platform.system() == "Windows":
        base_path = Path("C:/soap-web-services/server/db/drivers")
    else:
        base_path = Path("/opt/uniqa-web-services/server/db/drivers")
    
    driver1 = base_path / "jdbc-4.50.4.1.jar"
    driver2 = base_path / "bson-4.2.0.jar"

    for driver in [driver1, driver2]:
        if not driver.exists():
            logger.error(f"Missing driver file: {driver}")
            raise FileNotFoundError(driver)
    return str(driver1), str(driver2)

def connect_informix_storno():
    """Connect to Informix database with proper transaction handling"""
    user = Config.DB_USER
    password = Config.DB_PASSWORD
    host = Config.DB_HOST
    port = Config.DB_PORT
    dbname = Config.DB_NAME

    try:
        driver1, driver2 = get_informix_drivers()
        url = f"jdbc:informix-sqli://{host}:{port}/{dbname}:DB_LOCALE=en_US.utf8"
        
        conn = jaydebeapi.connect(
            "com.informix.jdbc.IfxDriver",
            url,
            [user, password],
            [driver1, driver2]
        )
        # Explicit transaction control
        # conn.jconn.setAutoCommit(False)
        cursor = conn.cursor()
        logger.info("Successfully connected to Informix DB with transaction support")
        return conn, cursor, True
        
    except Exception as e:
        logger.error(f"Connection failed: {str(e)}")
        return None, None, False

def connect_informix():
    """Connect to Informix database with proper transaction handling"""
    user = Config.DB_USER
    password = Config.DB_PASSWORD
    host = Config.DB_HOST
    port = Config.DB_PORT
    dbname = Config.DB_NAME

    try:
        driver1, driver2 = get_informix_drivers()
        url = f"jdbc:informix-sqli://{host}:{port}/{dbname}:DB_LOCALE=en_US.utf8"
        
        conn = jaydebeapi.connect(
            "com.informix.jdbc.IfxDriver",
            url,
            [user, password],
            [driver1, driver2]
        )
        # Explicit transaction control
        conn.jconn.setAutoCommit(False)
        cursor = conn.cursor()
        logger.info("Successfully connected to Informix DB with transaction support")
        return conn, cursor, True
        
    except Exception as e:
        logger.error(f"Connection failed: {str(e)}")
        return None, None, False


def parse_xml_date_to_parts(date_str: str) -> tuple:
    """Parse date string in DD-MM-YYYY or DD.MM.YYYY format into (month, day, year) tuple"""
    if not date_str:
        return (None, None, None)
    
    try:
        normalized = date_str.replace('.', '-')
        day, month, year = map(int, normalized.split('-'))
        return (month, day, year)
    except (ValueError, AttributeError) as e:
        logger.warning(f"Could not parse date string: {date_str} - {e}")
        return (None, None, None)

def insert_polisa_sertifikati(parsed_xml_data: dict, cursor=None, conn=None):
    """
    Inserts insurance registration data into polisa_sertifikati table
    Returns: (success: bool, message: str)
    """
    if not parsed_xml_data:
        return False, "Empty input data"

    sql = """
    INSERT INTO appuser.polisa_sertifikati (
        partner, gacid, certificate_id, tip, partner_reference_id,
        person_type, vat_number, title, last_name, first_name, country,
        zip, state, city, street, birth_place, birth_date, gender,
        phone, email, cover, valid_from, valid_to, valid_to_smo,
        currency_code, sum_insured, sum_insured_eur, premium,
        additional_premium, gross_premium
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
              MDY(?, ?, ?),  -- birth_date (month, day, year)
              ?,  -- gender
              ?, ?, ?,  -- phone, email, cover
              MDY(?, ?, ?),  -- valid_from (month, day, year)
              MDY(?, ?, ?),  -- valid_to (month, day, year)
              MDY(?, ?, ?),  -- valid_to_smo (month, day, year)
              ?, ?, ?, ?, ?, ?)  -- currency_code, sum_insured, sum_insured_eur, premium, additional_premium, gross_premium
    """
    
    # Manage connection lifecycle if not provided
    close_conn = False
    if cursor is None:
        conn, cursor, success = connect_informix()
        if not success:
            return False, "Database connection failed"
        close_conn = True
    
    try:
        insured_data = parsed_xml_data.get('Insured', {})
        policy_data = parsed_xml_data.get('Policy', {})

        # Parse dates into separate month, day, year components
        birth_month, birth_day, birth_year = parse_date_components(insured_data.get('BirthDateDMY', ''))
        valid_from_month, valid_from_day, valid_from_year = parse_date_components(policy_data.get('ValidFrom', ''))
        valid_to_month, valid_to_day, valid_to_year = parse_date_components(policy_data.get('ValidTo', '').replace('.', '-'))
        valid_to_smo_month, valid_to_smo_day, valid_to_smo_year = parse_date_components(policy_data.get('ValidToSMO', ''))

        # Prepare parameters
        params = [
            parsed_xml_data.get('Partner', ''),
            parsed_xml_data.get('GACID', ''),
            parsed_xml_data.get('CertificateID', ''),
            1,  # tip
            insured_data.get('PartnerReferenceID', ''),
            int(insured_data.get('PersonType', 1)),
            insured_data.get('VATNumber') or None,
            insured_data.get('Title', ''),
            insured_data.get('LastName', ''),
            insured_data.get('FirstName', ''),
            insured_data.get('Country', ''),
            insured_data.get('ZIP', ''),
            insured_data.get('State', ''),
            insured_data.get('City', ''),
            insured_data.get('Street', ''),
            insured_data.get('BirthPlace', ''),
            birth_month, birth_day, birth_year,  # MDY components
            (insured_data.get('Gender') or '')[:1].upper(),
            insured_data.get('Phone', ''),
            insured_data.get('Email', ''),
            policy_data.get('Cover', ''),
            valid_from_month, valid_from_day, valid_from_year,  # MDY components
            valid_to_month, valid_to_day, valid_to_year,  # MDY components
            valid_to_smo_month, valid_to_smo_day, valid_to_smo_year,  # MDY components
            policy_data.get('CurrencyCode', ''),
            float(policy_data.get('SumInsured', 0)),
            float(policy_data.get('SumInsuredEUR', 0)),
            float(policy_data.get('Premium', 0)),
            float(policy_data.get('AdditionalPremium', 0)),
            float(policy_data.get('GrossPremium', 0))
        ]

        logger.debug(f"Executing insert for {parsed_xml_data.get('GACID')}")
        logger.debug(f"SQL: {sql}")
        logger.debug(f"PARAMS: {params}")
        
        cursor.execute(sql, params)
        
        # Verify insertion by querying the database
        check_sql = "SELECT 1 FROM appuser.polisa_sertifikati WHERE certificate_id = ?"
        cursor.execute(check_sql, (parsed_xml_data.get('CertificateID'),))
        if not cursor.fetchone():
            logger.error("Insert operation completed but no row found in database")
            return False, "No row found in database after insert"
        if close_conn:
            conn.commit()


        return True, "Insert successful and verified"

    except Exception as e:
        logger.error(f"Database insert error: {str(e)}", exc_info=True)
        if conn:
            conn.rollback()
        return False, f"Insert failed: {str(e)}"
    finally:
        if close_conn and conn:
            try:
                conn.commit()  
                conn.close()
                cursor.close()
            except Exception as e:
                logger.error(f"Error closing connection: {str(e)}")

def parse_date_components(date_str: str) -> tuple:
    """Parse date string into (month, day, year) tuple"""
    if not date_str:
        return (None, None, None)
    
    try:
        normalized = date_str.replace('.', '-')
        day, month, year = map(int, normalized.split('-'))
        return (month, day, year)
    except (ValueError, AttributeError) as e:
        logger.error(f"Invalid date format: {date_str} - {str(e)}")
        raise ValueError(f"Invalid date format: {date_str}") from e

def call_generiraj_polisa_sertifikati(db_cursor, type: int, certificate_id: str):
    """
    Calls the Informix stored function 'generiraj_polisa_sertifikati'.
    """
    if not certificate_id:
        print("Error: Certificate ID is missing. Cannot call generiraj_polisa_sertifikati.")
        return None

    function_arg_literal_int = 6
    
    conn, cursor, success = connect_informix_storno()
    
    sql_call = "call generiraj_polisa_sertifikati(?, ?, ?)"
    
    print(f"\nCalling stored function: {sql_call}")
    print(f"  with Certificate ID: {certificate_id}, Argument 2: {function_arg_literal_int}")

    try:
        cursor.execute(sql_call, (certificate_id, type, function_arg_literal_int))
        result = cursor.fetchone()
        
        if result:
            print(f"Stored function 'generiraj_polisa_sertifikati' executed successfully.")
            print(f"  Return value(s): {result}")
            return result
        else:
            print(f"Stored function 'generiraj_polisa_sertifikati' executed. No explicit result row returned by fetchone().")
            return None

    except Exception as e:
        print(f"Error calling stored function 'generiraj_polisa_sertifikati': {e}")
        if hasattr(cursor, 'connection') and hasattr(cursor.connection, 'rollback'):
            cursor.connection.rollback()
    finally:
        cursor.close()
        conn.close()
    return None

def call_generiraj_polisa_sertifikati_1(db_cursor, type_request: int, certificate_id: str):
    """
    Alternative version of generiraj_polisa_sertifikati caller.
    """
    if not certificate_id:
        print("Error: Certificate ID is missing. Cannot call generiraj_polisa_sertifikati.")
        return None

    function_arg_literal_int = 6
    sql_call = "call generiraj_polisa_sertifikati(?,?,?)"
    
    print(f"\nCalling stored function: {sql_call}")
    print(f"  with Certificate ID: {certificate_id}, Argument 2: {function_arg_literal_int}")

    try:
        db_cursor.execute(sql_call, (certificate_id, type_request, function_arg_literal_int))
        print(sql_call)
        result = db_cursor.fetchone()
        
        if result:
            print(f"Stored function 'generiraj_polisa_sertifikati' executed successfully.")
            print(f"  Return value(s): {result}")
            return result
        else:
            print(f"Stored function 'generiraj_polisa_sertifikati' executed. No explicit result row returned by fetchone().")
            return None

    except Exception as e:
        print(f"Error calling stored function 'generiraj_polisa_sertifikati': {e}")
        if hasattr(db_cursor, 'connection') and hasattr(db_cursor.connection, 'rollback'):
            db_cursor.connection.rollback()
        return None

def call_generiraj_polisa_sertifikati_canceled(db_cursor, gacid: str, policy_number: str, 
                                             cancel_reason: str, cancel_date: str, 
                                             status_code: int = 6) -> dict:
    """
    Calls the Informix stored function for policy cancellation (storno).
    """
    result = {
        'success': False,
        'result': None,
        'error': None
    }
    
    if not all([gacid, policy_number, cancel_reason, cancel_date]):
        result['error'] = "Missing required parameters"
        return result
    
    try:
        sql = "call appuser.generiraj_polisa_sertifikati_canceled(?, ?, ?, ?, ?)"
        
        logger.info(f"Executing cancellation function for GACID: {gacid}, Policy: {policy_number}")
        logger.debug(f"SQL: {sql}")
        logger.debug(f"Params: ({gacid}, {policy_number}, {cancel_reason}, {cancel_date}, {status_code})")
        
        db_cursor.execute(sql, (gacid, policy_number, cancel_reason, cancel_date, status_code))
        func_result = db_cursor.fetchone()
        
        if func_result:
            result['success'] = True
            result['result'] = func_result
            logger.info(f"Cancellation function returned: {func_result}")
        else:
            result['error'] = "No result returned from function"
            logger.warning("Cancellation function executed but returned no result")
            
        return result
        
    except Exception as e:
        error_msg = f"Error executing cancellation function: {str(e)}"
        result['error'] = error_msg
        logger.error(error_msg, exc_info=True)
        
        try:
            if hasattr(db_cursor, 'connection'):
                db_cursor.connection.rollback()
        except Exception as rollback_error:
            logger.error(f"Rollback failed: {str(rollback_error)}")
            
        return result
    
def call_generiraj_polisa_sertifikati_status(cursor, gacid: str, status_code: int = 6) -> dict:
    """
    Calls generiraj_polisa_sertifikati_status and returns structured result.
    """
    result = {
        'success': False,
        'status_code': -1,
        'uniqa_offer_id': '',
        'policy_number': '',
        'policy_status': -1,
        'policy_status_comment': '',
        'error': None
    }
    
    try:
        query = "call appuser.generiraj_polisa_sertifikati_status(?, ?);"
        logger.debug(f"Executing: {query} with params: {gacid}, {status_code}")
        cursor.execute(query, (gacid, status_code))
        
        db_result = cursor.fetchone()
        if not db_result or len(db_result) < 5:
            result['error'] = "Incomplete result from procedure"
            return result
            
        result.update({
            'status_code': db_result[0],
            'uniqa_offer_id': db_result[1] or gacid,
            'policy_number': db_result[2] or '',
            'policy_status': db_result[3] if db_result[3] is not None else -1,
            'policy_status_comment': db_result[4] or ''
        })
        
        if result['status_code'] == 1:
            result['success'] = True
        print(f"Procedure call result: {result}")
        
        return result
                
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"Procedure call failed: {str(e)}", exc_info=True)
        return result

def parse_date(date_str):
    if not date_str or not isinstance(date_str, str):
        return None
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    logger.warning(f"Could not parse date: {date_str}")
    return None


def clean_value(value):
    if value is None:
        return ''
    if isinstance(value, str) and value.strip() == "":
        return ''
    return value
from typing import Optional, Union, Dict, Any
def format_datetime(dt: Optional[datetime]) -> Optional[str]:
    return dt.strftime('%Y-%m-%d %H:%M:%S') if dt else None
 
def insert_claim_data(claim_data: Union[Dict[str, Any], str], cursor: Any, conn: Any) -> bool:
    """
    Insert claim data into the polisa_Claim table. Assumes open connection and transaction are managed by the caller.
    """
    try:
        if isinstance(claim_data, str):
            claim_data = json.loads(claim_data)

        if not isinstance(claim_data, dict) or 'ReportClaim' not in claim_data:
            logger.error("Invalid claim data structure - missing ReportClaim")
            return False

        main_data = {
            'GACID': clean_value(claim_data.get('GACID')),
            'PolicyNumber': clean_value(claim_data.get('PolicyNumber')),
            'UniqaClaimID': clean_value(claim_data.get('UniqaClaimID'))
        }

        report_claim = claim_data['ReportClaim']
        combined_data = {**main_data, **report_claim}

        # Fetch column names to detect claim type column
        cursor.execute("""
            SELECT c.colname, c.coltype 
            FROM syscolumns c, systables t 
            WHERE t.tabname = 'polisa_claim' AND c.tabid = t.tabid
        """)
        columns = {row[0].lower(): row[1] for row in cursor.fetchall()}
        type_column = next((col for col in ['ctype', 'claimtype', 'type', 'clmtype'] if col in columns), None)

        if not type_column:
            logger.error("Could not find claim type column in database")
            return False

        sql = f"""
        INSERT INTO polisa_Claim (
            GACClaimID, PolicyNumber, UniqaClaimID,
            ClaimRegistrationCreated, CurrencyCode, ClaimDate,
            {type_column}, ClaimDescription, ClaimPlace_CountryCode,
            ClaimPlace_Address, Beneficiary_Individual,
            Beneficiary_LastName, Beneficiary_FirstName,
            Beneficiary_CountryCode, Beneficiary_Zip,
            Beneficiary_City, Beneficiary_Address,
            Beneficiary_Street, Beneficiary_PhoneNumber1,
            Beneficiary_Email, Date_Insert
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        values = (
            clean_value(combined_data.get('GACID')),
            clean_value(combined_data.get('PolicyNumber')),
            clean_value(combined_data.get('UniqaClaimID')) or "CLAIM_"+combined_data.get('GACID'),
            format_datetime(parse_date(combined_data.get('ClaimRegistrationCreated'))),
            clean_value(combined_data.get('CurrencyCode')),
            format_datetime(parse_date(combined_data.get('ClaimDate'))),
            clean_value(combined_data.get('Type')),
            clean_value(combined_data.get('ClaimDescription')),
            clean_value(combined_data.get('ClaimPlace_CountryCode')),
            clean_value(combined_data.get('ClaimPlace_Address')),
            clean_value(combined_data.get('Beneficiary_Individual')),
            clean_value(combined_data.get('Beneficiary_LastName')),
            clean_value(combined_data.get('Beneficiary_FirstName')),
            clean_value(combined_data.get('Beneficiary_CountryCode')),
            clean_value(combined_data.get('Beneficiary_Zip')),
            clean_value(combined_data.get('Beneficiary_City')),
            clean_value(combined_data.get('Beneficiary_Address')),
            clean_value(combined_data.get('Beneficiary_Street')),
            clean_value(combined_data.get('Beneficiary_PhoneNumber1')),
            clean_value(combined_data.get('Beneficiary_Email')),
            format_datetime(datetime.now())
        )

        logger.debug(f"Executing SQL: {sql}")
        logger.debug(f"With values: {values}")
        cursor.execute(sql, values)
        conn.commit()

        logger.info(f"Successfully inserted claim with GACID: {main_data['GACID']}")
        return True

    except Exception as e:
        logger.error(f"Error inserting claim data: {str(e)}", exc_info=True)
        return False
    # def insert_policy_certificate(cert_data: Union[dict, str]) -> bool:
    # """
    # Insert policy certificate data into the polisa_sertifikati table.
    # """
    # cursor = None
    # connection = None
    
    # try:
    #     if isinstance(cert_data, str):
    #         try:
    #             cert_data = json.loads(cert_data)
    #         except json.JSONDecodeError as e:
    #             logger.error(f"Invalid JSON input: {str(e)}")
    #             return False

    #     if not isinstance(cert_data, dict) or 'Insured' not in cert_data:
    #         logger.error("Invalid certificate data structure - missing Insured object")
    #         return False

    #     combined_data = {
    #         'GACID': cert_data.get('GACID'),
    #         'policy_number': cert_data.get('PolicyNumber'),
    #         **cert_data['Insured']
    #     }

    #     conn, cursor, success = connect_informix()
    #     if not success or not cursor:
    #         logger.error("Failed to establish database connection")
    #         return False

    #     sql = """
    #     INSERT INTO polisa_sertifikati (
    #         GACID, policy_number, partner, person_type, vat_number,
    #         Title, last_name, first_name, Country, ZIP,
    #         State, City, Street, birth_place, birth_date,
    #         Gender, Phone, Email, tip
    #     ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, MDY(?, ?, ?), ?, ?, ?, ?)
    #     """
        
    #     birth_month, birth_day, birth_year = None, None, None
    #     if combined_data.get('BirthDateDMY'):
    #         try:
    #             normalized_date = combined_data['BirthDateDMY'].replace('.', '-')
    #             day, month, year = map(int, normalized_date.split('-'))
    #             birth_month, birth_day, birth_year = month, day, year
    #         except (ValueError, AttributeError) as e:
    #             logger.error(f"Invalid birth date format: {combined_data['BirthDateDMY']}")
    #             return False

    #     values = (
    #         combined_data.get('GACID'),
    #         combined_data.get('policy_number'),
    #         combined_data.get('PartnerReferenceID', '#REFID'),
    #         int(combined_data.get('PersonType', 1)),
    #         combined_data.get('VATNumber', ''),
    #         combined_data.get('Title', 'Dr.'),
    #         combined_data.get('LastName'),
    #         combined_data.get('FirstName'),
    #         combined_data.get('Country', 'HU'),
    #         combined_data.get('ZIP', '1062'),
    #         combined_data.get('State', 'Pest'),
    #         combined_data.get('City', 'BUDAPEST'),
    #         combined_data.get('Street', 'Utca'),
    #         combined_data.get('BirthPlace', 'BUDAPEST'),
    #         birth_month,
    #         birth_day,
    #         birth_year,
    #         combined_data.get('Gender', 'Female')[:1].upper(),
    #         combined_data.get('Phone', '+36703330819'),
    #         combined_data.get('Email', 'E-mail'),
    #         2
    #     )
        
    #     logger.debug(f"Executing SQL: {sql}")
    #     logger.debug(f"With values: {values}")
        
    #     cursor.execute(sql, values)
    #     conn.commit()
    #     if hasattr(cursor, 'connection') and hasattr(cursor.connection, 'commit'):
    #         cursor.connection.commit()
        
    #     logger.info(f"Successfully inserted certificate with GACID: {combined_data.get('GACID')}")
    #     return True
        
    # except Exception as e:
    #     logger.error(f"Error inserting certificate data: {str(e)}", exc_info=True)
    #     if cursor and hasattr(cursor, 'connection') and hasattr(cursor.connection, 'rollback'):
    #         try:
    #             cursor.connection.rollback()
    #         except Exception as rollback_error:
    #             logger.error(f"Rollback failed: {str(rollback_error)}")
    #     return False
    # finally:
    #     if cursor:
    #         try:
    #             cursor.close()
    #         except Exception as e:
    #             logger.warning(f"Error closing cursor: {str(e)}")
    #     if connection:
    #         try:
    #             connection.close()
    #         except Exception as e:
    #             logger.warning(f"Error closing connection: {str(e)}")

def call_generiraj_polisa_claim(db_cursor, certificate_id: str, tip: int, user_id: int) -> dict:
    """
    Calls the Informix stored function 'generiraj_polisa_claim' for claim processing.
    """
    result = {
        'success': False,
        'result': None,
        'error': None
    }
    
    if not certificate_id:
        result['error'] = "Certificate ID is required"
        return result
    
    try:
        sql = "call appuser.generiraj_polisa_claim(?, ?, ?)"
        
        logger.info(f"Calling generiraj_polisa_claim with certificate_id: {certificate_id}")
        logger.debug(f"SQL: {sql}")
        logger.debug(f"Params: ({certificate_id}, {tip}, {user_id})")
        
        db_cursor.execute(sql, (certificate_id, tip, user_id))
        func_result = db_cursor.fetchone()
        
        if func_result:
            result['success'] = True
            result['result'] = func_result
            logger.info(f"Function returned: {func_result}")
        else:
            result['error'] = "Function executed but returned no result"
            logger.warning(result['error'])
            
        return result
        
    except Exception as e:
        error_msg = f"Error calling generiraj_polisa_claim: {str(e)}"
        result['error'] = error_msg
        logger.error(error_msg, exc_info=True)
        
        try:
            if hasattr(db_cursor, 'connection'):
                db_cursor.connection.rollback()
        except Exception as rollback_error:
            logger.error(f"Rollback failed: {str(rollback_error)}")
            
        return result

def call_generiraj_polisa_claim_status(db_cursor, certificate_id: str, policy_number: str, 
                                     uniqa_claim_id: str, user_id = 6) -> dict:
    """
    Calls the Informix stored function 'generiraj_polisa_claim_status' for claim status.
    """
    result = {
        'success': False,
        'result': None,
        'error': None
    }
    
    if not all([certificate_id, policy_number, uniqa_claim_id]):
        result['error'] = "Missing required parameters"
        return result
    
    try:
        sql = "call appuser.generiraj_polisa_claim_status(?, ?, ?, ?)"
        
        logger.info(f"Calling generiraj_polisa_claim_status for certificate: {certificate_id}")
        logger.debug(f"SQL: {sql}")
        logger.debug(f"Params: ({certificate_id}, {policy_number}, {uniqa_claim_id}, {user_id})")
        
        db_cursor.execute(sql, (certificate_id, policy_number, uniqa_claim_id, user_id))
        func_result = db_cursor.fetchone()
        
        if func_result:
            result['success'] = True
            result['result'] = func_result
            logger.info(f"Function returned: {func_result}")
        else:
            result['error'] = "Function executed but returned no result"
            logger.warning(result['error'])
            
        return result
        
    except Exception as e:
        error_msg = f"Error calling generiraj_polisa_claim_status: {str(e)}"
        result['error'] = error_msg
        logger.error(error_msg, exc_info=True)
        
        try:
            if hasattr(db_cursor, 'connection'):
                db_cursor.connection.rollback()
        except Exception as rollback_error:
            logger.error(f"Rollback failed: {str(rollback_error)}")
            
        return result       

# Initialize Java environment when module loads
set_java_home()
