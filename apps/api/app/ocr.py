import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path


class OCRUnavailableError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def get_ocr_engine():
    try:
        from paddleocr import PaddleOCR
    except ImportError as exc:
        raise OCRUnavailableError(
            "扫描件需要 PaddleOCR。请安装 requirements-ocr.txt 后重试"
        ) from exc
    return PaddleOCR(
        device="cpu",
        text_detection_model_name="PP-OCRv5_mobile_det",
        text_recognition_model_name="PP-OCRv5_mobile_rec",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )


def _texts_from_result(result) -> list[str]:
    payload = getattr(result, "json", {})
    if callable(payload):
        payload = payload()
    if not isinstance(payload, dict):
        return []
    data = payload.get("res", payload)
    return [str(text).strip() for text in data.get("rec_texts", []) if str(text).strip()]


def extract_scanned_pages(pdf_bytes: bytes, page_numbers: set[int]) -> dict[int, str]:
    if not page_numbers:
        return {}
    renderer = shutil.which("pdftoppm")
    if not renderer:
        raise OCRUnavailableError("扫描件 OCR 需要安装 Poppler（pdftoppm）")
    engine = get_ocr_engine()
    extracted: dict[int, str] = {}
    with tempfile.TemporaryDirectory(prefix="recall-ocr-") as temp_dir:
        source = Path(temp_dir) / "source.pdf"
        source.write_bytes(pdf_bytes)
        for page_number in sorted(page_numbers):
            prefix = Path(temp_dir) / f"page-{page_number}"
            process = subprocess.run(
                [renderer, "-f", str(page_number), "-l", str(page_number), "-r", "180", "-singlefile", "-png", str(source), str(prefix)],
                capture_output=True,
                text=True,
                timeout=90,
                check=False,
            )
            if process.returncode != 0:
                continue
            image_path = prefix.with_suffix(".png")
            if not image_path.exists():
                continue
            lines: list[str] = []
            for result in engine.predict(str(image_path)):
                lines.extend(_texts_from_result(result))
            if lines:
                extracted[page_number] = "\n".join(lines)
    return extracted


def extract_image(image_bytes: bytes, suffix: str = ".png") -> str:
    engine = get_ocr_engine()
    with tempfile.TemporaryDirectory(prefix="recall-image-ocr-") as temp_dir:
        image_path = Path(temp_dir) / f"source{suffix}"
        image_path.write_bytes(image_bytes)
        lines: list[str] = []
        for result in engine.predict(str(image_path)):
            lines.extend(_texts_from_result(result))
    return "\n".join(lines)
