"""Text extraction for office and plain-text documents."""

import re
import zipfile
from html import unescape
from io import BytesIO
from xml.etree import ElementTree


def _extract_docx(file_bytes: bytes) -> str:
    with zipfile.ZipFile(BytesIO(file_bytes)) as archive:
        xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    paragraphs = []
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    for paragraph in root.iter(f"{ns}p"):
        text = "".join(node.text or "" for node in paragraph.iter(f"{ns}t")).strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def _extract_rtf(file_bytes: bytes) -> str:
    text = file_bytes.decode("utf-8", errors="ignore")
    text = re.sub(r"\\'[0-9a-fA-F]{2}", "", text)
    text = re.sub(r"\\[a-zA-Z]+-?\d* ?", "", text)
    return re.sub(r"[{}]", "", text).strip()


def extract_text_from_document(file_bytes: bytes, filename: str) -> str:
    extension = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if extension == "docx":
        text = _extract_docx(file_bytes)
    elif extension in {"txt", "md", "markdown", "csv", "log"}:
        text = file_bytes.decode("utf-8-sig", errors="replace")
    elif extension in {"html", "htm"}:
        text = unescape(re.sub(r"<[^>]+>", " ", file_bytes.decode("utf-8", errors="replace")))
    elif extension == "rtf":
        text = _extract_rtf(file_bytes)
    else:
        raise ValueError(f"Unsupported document type: {extension}")
    text = text.replace("\x00", "").strip()
    if not text:
        raise ValueError("The document does not contain readable text")
    return text
