import os
import logging
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

logger = logging.getLogger(__name__)

def extract_text_from_file(file_path: str) -> str:
    """
    Extracts raw text from a given file path.
    Supports .txt, .md, and .pdf files.
    """
    if not os.path.exists(file_path):
        logger.warning(f"File not found: {file_path}")
        return ""

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        if fitz is None:
            logger.warning("PyMuPDF (fitz) is not installed. Cannot extract text from PDF.")
            return ""
        try:
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            return text
        except Exception as e:
            logger.error(f"Failed to read PDF {file_path}: {e}")
            return ""
    else:
        # Fallback to plain text for .txt, .md, etc.
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            logger.warning(f"Failed to decode {file_path} as utf-8. Trying latin-1.")
            try:
                with open(file_path, "r", encoding="latin-1") as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Failed to read {file_path}: {e}")
                return ""
        except Exception as e:
            logger.error(f"Failed to read {file_path}: {e}")
            return ""
