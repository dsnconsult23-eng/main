from lxml import etree as ET


DOCUMENT_PAYLOAD_TAGS = (
    "PDF", "Pdf", "pdf",
    "Document", "document",
    "Email", "EMail", "email",
    "EML", "Eml", "eml",
    "Mail", "mail",
)


def extract_document_payloads(documents_node: ET._Element | None) -> list[str]:
    """Extract supported base64 document payloads from a <Documents> node."""
    if documents_node is None:
        return []

    payloads: list[str] = []
    for tag_name in DOCUMENT_PAYLOAD_TAGS:
        for node in documents_node.findall(tag_name):
            if node.text and node.text.strip():
                payloads.append(node.text.strip())
    return payloads
