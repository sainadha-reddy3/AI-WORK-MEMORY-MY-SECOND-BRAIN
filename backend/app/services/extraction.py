"""
Text extraction from uploaded files.

Everything produced here is DERIVED data — category 2 in the project's
source rules ("extracted from uploaded files"). The original file is
always the source of truth; this text exists so its contents can be
searched.

For images, OCR reports a confidence for every word. Words it is
unsure of are marked [?word?]; words it cannot read become
[unreadable]. Nothing is silently guessed.
"""

import io
import re
from dataclasses import dataclass
from pathlib import PurePath

# Enough for very long documents without bloating the database.
MAX_CHARS = 200_000

# OCR word-confidence thresholds (Tesseract reports 0-100).
LOW_CONFIDENCE = 60   # below this: shown as [?word?]
UNREADABLE = 30       # below this: shown as [unreadable]

# Patterns that indicate a real credential inside a file's contents.
# Kept deliberately specific, so ordinary notes are never refused.
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),        # SSH / TLS private keys
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),                       # AWS access key id
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),             # GitHub tokens
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),           # Slack tokens
    re.compile(r'"type"\s*:\s*"service_account"'),             # GCP service-account key file
    re.compile(r'"private_key"\s*:\s*"-----BEGIN'),            # any JSON-embedded private key
]


def extract_text(data: bytes, filename: str, content_type: str, kind: str) -> str | None:
    """
    Return the readable text inside a non-image file, or None.

    Never raises — a file whose text can't be read is still stored.
    Images are handled separately by ocr_image().
    """
    suffix = PurePath(filename.lower()).suffix

    try:
        if kind == "code" or suffix in {".txt", ".md"} or content_type.startswith("text/"):
            text = data.decode("utf-8", errors="replace")

        elif suffix == ".pdf" or content_type == "application/pdf":
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)

        elif suffix == ".docx":
            import docx

            document = docx.Document(io.BytesIO(data))
            text = "\n".join(p.text for p in document.paragraphs)

        else:
            return None

    except Exception:
        return None

    # Null bytes are not allowed in Postgres text columns.
    text = text.replace("\x00", "").strip()
    return text[:MAX_CHARS] or None


def looks_like_secret(text: str) -> bool:
    """True if the text contains something that looks like a real credential."""
    return any(p.search(text) for p in SECRET_PATTERNS)


# ------------------------------------------------------------------
# OCR
# ------------------------------------------------------------------


@dataclass
class OcrResult:
    text: str | None
    confidence: float | None  # average word confidence, 0-100
    words: int
    uncertain_words: int


def _prepare_image(image):
    """Make an image easier for Tesseract to read."""
    from PIL import ImageOps, ImageStat

    # Phone photos often carry a rotation flag rather than rotated pixels.
    img = ImageOps.exif_transpose(image)
    img = img.convert("L")  # greyscale

    # Tesseract prefers dark text on a light background. Terminals and
    # K9s are the opposite, so flip dark images.
    if ImageStat.Stat(img).mean[0] < 110:
        img = ImageOps.invert(img)

    # Small screenshots read far better when enlarged first.
    if img.width < 1600:
        factor = min(2.0, 1600 / img.width)
        img = img.resize((int(img.width * factor), int(img.height * factor)))

    return ImageOps.autocontrast(img)


def ocr_image(data: bytes, langs: str = "eng") -> OcrResult:
    """
    Read text from an image, word by word, keeping Tesseract's confidence.

    Low-confidence words are marked rather than trusted, so the result
    can never read more certain than the machine actually was.
    """
    try:
        import pytesseract
        from PIL import Image

        img = _prepare_image(Image.open(io.BytesIO(data)))
        d = pytesseract.image_to_data(img, lang=langs, output_type=pytesseract.Output.DICT)
    except Exception:
        return OcrResult(None, None, 0, 0)

    lines: dict = {}
    confidences: list[float] = []
    uncertain = 0

    for i, raw_word in enumerate(d["text"]):
        word = str(raw_word).strip()
        if not word:
            continue
        conf = float(d["conf"][i])
        if conf < 0:
            continue

        if conf < UNREADABLE:
            token = "[unreadable]"
            uncertain += 1
        elif conf < LOW_CONFIDENCE:
            token = f"[?{word}?]"
            uncertain += 1
        else:
            token = word

        key = (d["block_num"][i], d["par_num"][i], d["line_num"][i])
        lines.setdefault(key, []).append(token)
        confidences.append(conf)

    if not confidences:
        return OcrResult(None, None, 0, 0)

    text = "\n".join(" ".join(tokens) for tokens in lines.values())
    # Collapse runs like "[unreadable] [unreadable] [unreadable]".
    text = re.sub(r"(\[unreadable\]\s*){2,}", "[unreadable] ", text).strip()

    return OcrResult(
        text=text[:MAX_CHARS] or None,
        confidence=round(sum(confidences) / len(confidences), 1),
        words=len(confidences),
        uncertain_words=uncertain,
    )
# ------------------------------------------------------------------
# One entry point for every kind of file
# ------------------------------------------------------------------


@dataclass
class Extraction:
    text: str | None
    method: str | None       # "text" | "pdf" | "docx" | "ocr"
    confidence: float | None  # only for OCR


IMAGE_KINDS = {"screenshot", "image", "notebook_photo"}


def extract_any(
    data: bytes, filename: str, content_type: str, kind: str, ocr_langs: str = "eng"
) -> Extraction:
    """Extract text from any supported file, recording how it was obtained."""
    if kind in IMAGE_KINDS or (content_type or "").startswith("image/"):
        result = ocr_image(data, langs=ocr_langs)
        return Extraction(result.text, "ocr" if result.text else None, result.confidence)

    text = extract_text(data, filename, content_type or "", kind)
    suffix = PurePath(filename.lower()).suffix
    method = "pdf" if suffix == ".pdf" else "docx" if suffix == ".docx" else "text"
    return Extraction(text, method if text else None, None)