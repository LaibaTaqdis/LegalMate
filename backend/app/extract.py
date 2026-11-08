"""Reads the text out of an uploaded file: PDF, Word (docx), JPG or PNG. Scanned pages and photos are read with OCR, in English and Urdu.

Safety stance: the file is untrusted. The type is decided from the file's own bytes (not its name), size / page / pixel / zip limits
are enforced before heavy work, nothing in the file is ever executed (no macros, no scripts), and the original is not kept.

OCR design. Two readers share one picture:
  * the English reader (`rapidocr-onnxruntime`, always on) reads Latin letters and digits quickly and accurately;
  * the Urdu reader (`rapidocr` with the PaddleOCR Arabic-script model, `OCR_LANGS` contains "ur") reads Urdu, Persian and Arabic script.
The Urdu reader only runs when the English reader left a real share of the page's ink unread (so plain English pages cost nothing extra).
Each line is kept from whichever reader is right for its script, and lines are put back in reading order (right to left for Urdu).
Measured on rendered Urdu text: about 85% of each line correct on clean print (the English reader: 0%). Known weakness: it often reads
ہ as ب. Nastaliq print and handwriting are not tested and will be worse. The user is always told when text came from an image.

Runtime module: it must not import `ingest/`.
"""
from __future__ import annotations

import io
import logging
import re
import threading
import time
import zipfile
from dataclasses import dataclass, field

from .config import DocSettings
from .urdu import arabic_fraction, fold_presentation_forms, garbled_fraction, urduize

log = logging.getLogger("legalmate.extract")
logging.getLogger("RapidOCR").setLevel(logging.WARNING)


class ExtractError(Exception):
    """A problem the user can understand and act on. `status` and `code` follow the API's error table."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


@dataclass
class Extracted:
    text: str
    pages: int
    file_type: str
    ocr_pages: int = 0
    ocr_conf: float | None = None
    truncated: bool = False
    urdu: bool = False
    warnings: list[str] = field(default_factory=list)


@dataclass
class OcrResult:
    text: str
    conf: float
    urdu_lines: int = 0
    urdu_failed: bool = False


# ------------------------------------------------------------------------------------------------ type from the bytes
def sniff(data: bytes) -> str:
    head = data[:2048]
    if head.startswith(b"%PDF-") or b"%PDF-" in head[:1024]:
        return "pdf"
    if head.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                if "word/document.xml" in z.namelist():
                    return "docx"
        except zipfile.BadZipFile:
            pass
    raise ExtractError(415, "UNSUPPORTED_TYPE", "This file type is not supported. Please upload a PDF, Word (.docx), JPG or PNG file.")


# ------------------------------------------------------------------------------------------------ OCR engines (loaded once, on first use)
_lock = threading.Lock()
_latin = None
_urdu = None
_urdu_error: str | None = None
_slots: threading.Semaphore | None = None


def _slots_get(cfg: DocSettings) -> threading.Semaphore:
    global _slots
    with _lock:
        if _slots is None:
            _slots = threading.Semaphore(cfg.ocr_concurrency)
    return _slots


def _latin_get():
    """English reader. Loading takes a few seconds and ~200 MB."""
    global _latin
    with _lock:
        if _latin is None:
            try:
                from rapidocr_onnxruntime import RapidOCR
            except ImportError as e:                                   # pragma: no cover - depends on the install
                raise ExtractError(503, "UNAVAILABLE", "Reading scanned documents is not available on this server.") from e
            _latin = RapidOCR()
            _bucket_recognizer(_latin)
    return _latin


REC_WIDTH_STEP = 160                          # text-line crops are padded to a multiple of this many pixels (see _bucket_recognizer)


def _bucket_recognizer(reader) -> None:
    """Make the English reader fast on a photo of a size it has not seen before.

    Its recognizer pads every batch of text lines to a width that depends on the longest line in the batch, so almost every new picture
    produces new tensor shapes, and the runtime pays a one-off set-up cost for each shape: measured 12 s for the first reading of a
    picture, 3-4 s for the second reading of the same one. Rounding the width up to a multiple of 160 px (and reading one line at a
    time) leaves a handful of shapes in total, so after the first few lines every picture is fast. Extra white padding on the right
    does not change what the recognizer reads (measured: same text, same line count)."""
    try:
        rec = reader.text_rec
        original = rec.resize_norm_img

        def bucketed(img, max_wh_ratio, _orig=original):
            width = max(REC_WIDTH_STEP, -(-int(48 * max_wh_ratio) // REC_WIDTH_STEP) * REC_WIDTH_STEP)
            return _orig(img, (width + 0.5) / 48)

        rec.resize_norm_img = bucketed
        rec.rec_batch_num = 1
    except Exception:                                                  # noqa: BLE001 - a different version of the package: keep its own behaviour
        log.warning("could not set up fixed-width text recognition; images will read more slowly the first time", exc_info=True)


def warm(cfg: DocSettings) -> float:
    """Load both readers and run them once, so the first user upload does not pay for model loading and first-run set-up.
    The English recognizer is also run once per width it will meet (a few seconds in total). Returns the seconds it took."""
    import numpy as np
    from PIL import Image, ImageDraw

    t0 = time.time()
    img = Image.new("RGB", (900, 120), "white")
    ImageDraw.Draw(img).text((20, 40), "LegalMate OCR warm-up 123", fill="black")
    ocr_image(img, cfg)
    reader = _latin_get()
    with _slots_get(cfg):
        for width in range(REC_WIDTH_STEP, 1601, REC_WIDTH_STEP):       # every width a normal line is rounded to
            reader.text_rec([np.full((48, width, 3), 255, dtype=np.uint8)])
    if "ur" in cfg.ocr_langs:
        urdu = _urdu_get(cfg)
        if urdu is not None:                                            # its text detector and recognizer are created on the first line it sees
            with _slots_get(cfg):
                urdu(np.array(img))
    return time.time() - t0


def _urdu_get(cfg: DocSettings):
    """Urdu reader, or None if it cannot be loaded (the failure is remembered, so a missing model does not slow down every page).
    The first start downloads the model once (about 10 MB, from the RapidOCR model repository); `python -m app.ocr_warmup` does that ahead of time."""
    global _urdu, _urdu_error
    with _lock:
        if _urdu is None and _urdu_error is None:
            try:
                from rapidocr import LangRec, ModelType, OCRVersion, RapidOCR
                ver = OCRVersion.PPOCRV4 if cfg.ocr_urdu_model == "v4" else OCRVersion.PPOCRV5
                _urdu = RapidOCR(params={"Rec.lang_type": LangRec.ARABIC, "Rec.ocr_version": ver, "Rec.model_type": ModelType.MOBILE})
            except Exception as e:                                     # noqa: BLE001 - not installed, no model, offline...
                _urdu_error = f"{type(e).__name__}: {str(e)[:200]}"
                log.warning("Urdu OCR is not available: %s", _urdu_error)
    return _urdu


def urdu_available(cfg: DocSettings) -> bool:
    return "ur" in cfg.ocr_langs and _urdu_get(cfg) is not None


@dataclass
class _Line:
    x0: float
    y0: float
    x1: float
    y1: float
    text: str
    score: float
    arabic: bool

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2


def _bbox(box) -> tuple[float, float, float, float]:
    xs, ys = [float(p[0]) for p in box], [float(p[1]) for p in box]
    return min(xs), min(ys), max(xs), max(ys)


def _ink_outside(gray, lines: list[_Line]) -> float:
    """Share of the page's ink that lies outside every line the English reader found.

    Ink is a pixel clearly darker than its own neighbourhood (strokes of writing), not a pixel below a fixed grey level: on a phone photo
    a shadow, a dark desk or an uneven light would otherwise count as unread writing and start the slow Urdu reader on an English page
    (measured: 5-7 s wasted on every photo). The check runs on a reduced copy, so it costs a few milliseconds."""
    import numpy as np
    from PIL import Image, ImageFilter

    h, w = gray.shape
    scale = min(1.0, 1400 / max(h, w))
    small = Image.fromarray(gray)
    if scale < 1.0:
        small = small.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.BILINEAR)
    sm = np.asarray(small, dtype=np.int16)
    local = np.asarray(small.filter(ImageFilter.BoxBlur(max(6, round(22 * scale)))), dtype=np.int16)
    ink = (local - sm) > 38
    sh, sw = ink.shape
    try:                                                    # long structures are not writing: the paper's edge, table rules, page borders
        import cv2
        _, labels, stats, _ = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
        long_ = (stats[:, cv2.CC_STAT_WIDTH] > 0.2 * max(sh, sw)) | (stats[:, cv2.CC_STAT_HEIGHT] > 0.2 * max(sh, sw))
        long_[0] = False
        ink &= ~long_[labels]
    except Exception:                                       # noqa: BLE001 - OpenCV comes with the OCR packages; without it the plain measure is used
        pass
    total = int(ink.sum())
    if total < 150:
        return 0.0
    mask = np.zeros(ink.shape, dtype=bool)
    pad = 6 * scale
    for ln in lines:
        mask[max(0, int(ln.y0 * scale - pad)): min(sh, int(ln.y1 * scale + pad) + 1), max(0, int(ln.x0 * scale - pad)): min(sw, int(ln.x1 * scale + pad) + 1)] = True
    return float(ink[~mask].sum() / total)


def _in_reading_order(lines: list[_Line]) -> str:
    """Top to bottom; inside one row, right to left when the row is mostly Arabic script, left to right otherwise."""
    if not lines:
        return ""
    heights = sorted(max(1.0, ln.y1 - ln.y0) for ln in lines)
    tol = 0.6 * heights[len(heights) // 2]
    rows: list[list[_Line]] = []
    for ln in sorted(lines, key=lambda l: l.cy):
        if rows and abs(ln.cy - sum(x.cy for x in rows[-1]) / len(rows[-1])) <= tol:
            rows[-1].append(ln)
        else:
            rows.append([ln])
    out = []
    for row in rows:
        rtl = sum(1 for x in row if x.arabic) * 2 > len(row)
        out.append(" ".join(x.text for x in sorted(row, key=lambda l: -l.cx if rtl else l.cx)))
    return "\n".join(out)


def ocr_image(img, cfg: DocSettings) -> OcrResult:
    """Text and average confidence (0-1) of a PIL image, in English and (when enabled and needed) Urdu."""
    import numpy as np
    from PIL import ImageOps

    # The text detector can silently miss a line that sits close to the picture's edge (measured: a whole line vanished from a
    # 1500 px image). A white margin around the picture fixes it every time.
    img = ImageOps.expand(img.convert("RGB"), border=max(40, round(max(img.size) * 0.04)), fill="white")
    arr = np.array(img)
    slots = _slots_get(cfg)

    with slots:
        res, _ = _latin_get()(arr)
    lines = [_Line(*_bbox(r[0]), str(r[1]), float(r[2]), arabic_fraction(str(r[1])) >= cfg.ocr_script_min) for r in (res or [])]
    # The English reader invents symbol-soup and single letters when it is shown script it cannot read (measured on Urdu: "oLb Sjl>~l", "V").
    # Such lines are dropped; real English lines (letters, digits, ordinary punctuation) are never affected.
    lines = [ln for ln in lines if sum(c.isalnum() for c in ln.text) >= 2
             and not (garbled_fraction(ln.text) > 0.2 and ln.score < 0.9) and not (garbled_fraction(ln.text) > 0.05 and ln.score < 0.65)]

    urdu_lines, failed = 0, False
    if "ur" in cfg.ocr_langs and _ink_outside(np.array(img.convert("L")), lines) > cfg.ocr_urdu_trigger:
        eng = _urdu_get(cfg)
        if eng is None:
            failed = True
        else:
            with slots:
                out = eng(arr)
            boxes = out.boxes if out.boxes is not None else []
            found = [_Line(*_bbox(b), t, float(s), True) for b, t, s in zip(boxes, out.txts or [], out.scores or [])]
            found = [f for f in found if f.score >= cfg.ocr_urdu_min_score and arabic_fraction(f.text) >= cfg.ocr_script_min]
            if found:
                # an English-reader line that sits inside an Urdu line is that same line misread: the Urdu reading wins
                lines = [e for e in lines if not any(f.x0 - 4 <= e.cx <= f.x1 + 4 and f.y0 - 4 <= e.cy <= f.y1 + 4 for f in found) or e.arabic]
                lines += found
                urdu_lines = len(found)
    text = _in_reading_order(lines)
    if urdu_lines:
        text = urduize(text)
    conf = sum(ln.score for ln in lines) / len(lines) if lines else 0.0
    return OcrResult(text, conf, urdu_lines, failed)


# ------------------------------------------------------------------------------------------------ cleaning
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean(text: str) -> str:
    text = _CTRL.sub("", fold_presentation_forms(text.replace("\r\n", "\n").replace("\r", "\n")))
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _urdu_notes(res: Extracted, cfg: DocSettings, *, urdu_lines: int, urdu_failed: bool) -> None:
    if urdu_lines:
        res.urdu = True
        res.warnings.append("Urdu text read from an image can contain mistakes, such as similar-looking letters. "
                            "Please check names, amounts and dates against your original.")
    if urdu_failed:
        res.warnings.append("This document seems to contain Urdu text in an image, but the Urdu reader is not available on this server, so that text was not read.")


# ------------------------------------------------------------------------------------------------ the readers
def _read_pdf(data: bytes, cfg: DocSettings) -> Extracted:
    import pymupdf as fitz

    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as e:
        raise ExtractError(422, "UNREADABLE", "This PDF could not be opened. It may be damaged.") from e
    with doc:
        if doc.needs_pass or doc.is_encrypted:
            raise ExtractError(422, "PASSWORD_PROTECTED", "This PDF is password protected. Please remove the password and upload it again.")
        n = doc.page_count
        if n == 0:
            raise ExtractError(422, "UNREADABLE", "This PDF has no pages.")
        if n > cfg.max_pages:
            raise ExtractError(422, "TOO_MANY_PAGES", f"This PDF has {n} pages. The limit is {cfg.max_pages}. Please upload the pages that matter.")
        parts, ocr_pages, confs, urdu_total, urdu_failed = [], 0, [], 0, False
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            broken = garbled_fraction(text) > 0.15                                       # old Urdu files (InPage) have an unreadable text layer
            if (len(text.strip()) < cfg.ocr_min_page_chars or broken) and cfg.ocr_enabled:     # a scan: read it from the picture
                from PIL import Image

                pix = page.get_pixmap(dpi=cfg.ocr_dpi)
                if pix.width * pix.height > cfg.max_image_pixels:
                    raise ExtractError(422, "TOO_LARGE_IMAGE", "A page of this PDF is too large to read. Please upload a smaller scan.")
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples) if pix.n == 3 else Image.open(io.BytesIO(pix.tobytes("png")))
                r = ocr_image(img, cfg)
                urdu_total += r.urdu_lines
                urdu_failed = urdu_failed or r.urdu_failed
                if r.text.strip():
                    text = r.text
                    ocr_pages += 1
                    confs.append(r.conf)
                elif broken:
                    text = ""
            parts.append(f"[Page {i}]\n{clean(text)}")
        conf = sum(confs) / len(confs) if confs else None
        res = Extracted("\n\n".join(parts), n, "pdf", ocr_pages, conf)
        if conf is not None and conf < cfg.ocr_min_confidence:
            res.warnings.append("Some pages are scans that were hard to read, so parts of the text may be wrong. A clearer copy gives a better result.")
        _urdu_notes(res, cfg, urdu_lines=urdu_total, urdu_failed=urdu_failed)
        res.text = urduize(res.text)                                                     # digital Urdu: Arabic letter forms -> Urdu letters
        res.urdu = res.urdu or arabic_fraction(res.text) > 0.3
        return res


def _read_docx(data: bytes, cfg: DocSettings) -> Extracted:
    from docx import Document

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:                                  # zip-bomb guard before python-docx unpacks anything
            infos = z.infolist()
            if len(infos) > 5000 or sum(i.file_size for i in infos) > cfg.docx_max_uncompressed_mb * 1024 * 1024:
                raise ExtractError(422, "UNREADABLE", "This Word file is too large or complex to read safely.")
        doc = Document(io.BytesIO(data))
    except ExtractError:
        raise
    except Exception as e:
        raise ExtractError(422, "UNREADABLE", "This Word file could not be opened. It may be damaged or password protected.") from e
    out: list[str] = []
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    for child in doc.element.body.iterchildren():                                     # paragraphs and tables in document order
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            out.append(Paragraph(child, doc).text)
        elif tag == "tbl":
            for row in Table(child, doc).rows:
                seen, cells = set(), []
                for c in row.cells:                                                   # merged cells repeat: keep each once
                    if id(c._tc) not in seen:
                        seen.add(id(c._tc))
                        cells.append(c.text.strip())
                out.append(" | ".join(x for x in cells if x))
    text = urduize(clean("\n".join(out)))
    pages = max(1, -(-len(text) // 3000))                                              # Word has no fixed pages: about 3000 characters each
    if pages > cfg.max_pages:
        raise ExtractError(422, "TOO_MANY_PAGES", f"This document is about {pages} pages long. The limit is {cfg.max_pages}.")
    res = Extracted(text, pages, "docx")
    res.urdu = arabic_fraction(text) > 0.3
    return res


def check_image(data: bytes, cfg: DocSettings) -> None:
    """The quick part of reading a photo, with no OCR: is it a picture that can be opened, and not absurdly large? Raises ExtractError.
    Used to accept a chat photo at once and read it later."""
    from PIL import Image

    Image.MAX_IMAGE_PIXELS = cfg.max_image_pixels
    try:
        img = Image.open(io.BytesIO(data))
        if img.width * img.height > cfg.max_image_pixels:
            raise ExtractError(422, "TOO_LARGE_IMAGE", "This image is too large to read. Please upload a smaller photo.")
        img.verify()
    except ExtractError:
        raise
    except Exception as e:                                                             # includes DecompressionBombError
        raise ExtractError(422, "UNREADABLE", "This image could not be opened. It may be damaged.") from e


def compact_image(data: bytes, kind: str, cfg: DocSettings) -> tuple[bytes, str]:
    """A big phone photo made smaller before it is stored for reading later: at most 3000 px on the long side, as a JPEG (a 4-8 MB photo
    becomes about 1 MB, so the upload to the database is quick). Reading is unaffected: text is just as readable at 3000 px (measured:
    same text at 3000 and 4000 px). Small pictures are kept as they are."""
    from PIL import Image, ImageOps

    if len(data) <= 1_000_000:
        try:
            if max(Image.open(io.BytesIO(data)).size) <= 3000:
                return data, kind
        except Exception:                                                              # noqa: BLE001 - check_image has already accepted it
            return data, kind
    try:
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
        img.thumbnail((3000, 3000))
        out = io.BytesIO()
        img.convert("RGB").save(out, "JPEG", quality=88)
        return out.getvalue(), "jpg"
    except Exception:                                                                  # noqa: BLE001 - keep the original rather than fail the upload
        return data, kind


def _read_image(data: bytes, file_type: str, cfg: DocSettings) -> Extracted:
    from PIL import Image, ImageOps

    if not cfg.ocr_enabled:
        raise ExtractError(503, "UNAVAILABLE", "Reading photos is switched off on this server. Please upload a PDF or Word file.")
    Image.MAX_IMAGE_PIXELS = cfg.max_image_pixels
    try:
        img = Image.open(io.BytesIO(data))
        if img.width * img.height > cfg.max_image_pixels:
            raise ExtractError(422, "TOO_LARGE_IMAGE", "This image is too large to read. Please upload a smaller photo.")
        img = ImageOps.exif_transpose(img)
        img.load()
    except ExtractError:
        raise
    except Exception as e:                                                             # includes DecompressionBombError
        raise ExtractError(422, "UNREADABLE", "This image could not be opened. It may be damaged.") from e
    if max(img.size) > 3500:                                                           # no gain from huge photos, and OCR time grows with size
        img.thumbnail((3500, 3500))
    r = ocr_image(img, cfg)
    res = Extracted(clean(r.text), 1, file_type, 1, r.conf)
    if r.conf < cfg.ocr_min_confidence:
        res.warnings.append("This photo was hard to read, so parts of the text may be wrong. A sharper, well-lit photo gives a better result.")
    _urdu_notes(res, cfg, urdu_lines=r.urdu_lines, urdu_failed=r.urdu_failed)
    return res


def extract(data: bytes, cfg: DocSettings) -> Extracted:
    """Raises ExtractError with a plain message for anything the user can fix."""
    kind = sniff(data)
    res = _read_pdf(data, cfg) if kind == "pdf" else _read_docx(data, cfg) if kind == "docx" else _read_image(data, kind, cfg)
    res.text = res.text.strip()
    if res.ocr_pages:                                   # OCR can misread digits (seen: "45,000" read as "45,0o0"), and amounts matter in a contract
        res.warnings.insert(0, "Part of this document was read from an image. Please double-check amounts, dates and names against the original.")
    if len(re.sub(r"\[Page \d+\]|\s", "", res.text)) < 20:
        raise ExtractError(422, "NO_TEXT", "We could not find readable text in this file. If it is a photo or scan, try a clearer, well-lit copy.")
    if len(res.text) > cfg.max_text_chars:
        res.text, res.truncated = res.text[: cfg.max_text_chars], True
        res.warnings.append(f"The document is very long, so only the first {cfg.max_text_chars:,} characters were kept.")
    return res
