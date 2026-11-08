"""Safe file validation and text extraction."""
import io
import re

ALLOWED = {
    ".pdf": ("application/pdf", [b"%PDF-"]),
    ".docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", [b"PK\x03\x04"]),
    ".txt": ("text/plain", None),
    ".png": ("image/png", [b"\x89PNG\r\n\x1a\n"]),
    ".jpg": ("image/jpeg", [b"\xff\xd8\xff"]),
    ".jpeg": ("image/jpeg", [b"\xff\xd8\xff"]),
    ".webp": ("image/webp", [b"RIFF"]),
}


class InvalidFile(Exception):
    pass


def validate(filename: str, head: bytes) -> tuple[str, str]:
    name = (filename or "").lower()
    ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""
    if ext not in ALLOWED:
        raise InvalidFile("Upload a PDF, DOCX, TXT, PNG, JPG or WEBP file.")
    ctype, magics = ALLOWED[ext]
    if magics and not any(head.startswith(m) for m in magics):
        raise InvalidFile("The file contents don't match its type.")
    if ext == ".txt":
        try:
            head.decode("utf-8")
        except UnicodeDecodeError:
            raise InvalidFile("Text files must be UTF-8.")
    return ext, ctype


def safe_name(filename: str) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", filename)[-120:]
    return base or "file"


def extract_text(data: bytes, ext: str) -> str:
    if ext == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return "\n".join((p.extract_text() or "") for p in reader.pages[:300])
    if ext == ".docx":
        import docx

        d = docx.Document(io.BytesIO(data))
        return "\n".join(p.text for p in d.paragraphs)
    if ext == ".txt":
        return data.decode("utf-8", errors="ignore")
    return ""  # images: analysed visually by the AI, no text layer


def chunk(text: str, size=1200, overlap=150):
    text = re.sub(r"\s+\n", "\n", text).strip()
    i = 0
    while i < len(text):
        yield text[i:i + size]
        i += size - overlap
