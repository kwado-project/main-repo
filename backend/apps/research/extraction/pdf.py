"""PDF → text with page markers, using the text layer and Tesseract OCR for scanned pages."""
import io
import logging
import shutil
from dataclasses import dataclass, field

logger = logging.getLogger("kwado.research")
MIN_TEXT_CHARS = 40   # less than this on a page → treat it as scanned and OCR it
OCR_DPI = 300
MAX_PAGES = 400


@dataclass
class PdfText:
    text: str
    pages: int
    ocr_pages: list = field(default_factory=list)
    images: list = field(default_factory=list)   # (page_number, bytes, ext)
    warnings: list = field(default_factory=list)

    @property
    def method(self) -> str:
        return "ocr" if self.ocr_pages and len(self.ocr_pages) >= self.pages / 2 else "pdf_text"


def ocr_available() -> bool:
    try:
        import pytesseract  # noqa: F401
    except ImportError:
        return False
    return shutil.which("tesseract") is not None


def pdf_to_text(data: bytes, *, extract_images: bool = True) -> PdfText:
    import pymupdf as fitz

    doc = fitz.open(stream=data, filetype="pdf")
    out, ocr_pages, images, warnings = [], [], [], []
    can_ocr = ocr_available()
    for i, page in enumerate(doc):
        if i >= MAX_PAGES:
            warnings.append(f"stopped after {MAX_PAGES} pages")
            break
        n = i + 1
        text = page.get_text("text") or ""
        if len(text.strip()) < MIN_TEXT_CHARS:
            if can_ocr:
                import pytesseract
                from PIL import Image

                pix = page.get_pixmap(dpi=OCR_DPI)
                text = pytesseract.image_to_string(Image.open(io.BytesIO(pix.tobytes("png"))), lang="eng")
                ocr_pages.append(n)
            else:
                warnings.append(f"page {n} looks scanned but OCR (tesseract) is not installed")
        out.append(f"\n[[PAGE:{n}]]\n{text}")
        if extract_images:
            for img in page.get_images(full=True)[:20]:
                try:
                    info = doc.extract_image(img[0])
                    if info and info.get("width", 0) >= 60 and info.get("height", 0) >= 60:
                        images.append((n, info["image"], info.get("ext", "png")))
                except Exception:  # noqa: BLE001
                    continue
    pages = min(len(doc), MAX_PAGES)
    doc.close()
    return PdfText("".join(out), pages, ocr_pages, images, warnings)
