"""
Text Extraction Utilities
Pure Python text extraction from PDF and image files
No Windows-specific dependencies required
"""

import logging
from pathlib import Path
from typing import Tuple
import io

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_content: bytes) -> str:
    """
    Extract text from PDF using pypdf and pdfplumber.
    Falls back between methods for best results.
    """
    text = ""
    
    # Try pypdf first (faster, works for most PDFs)
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(file_content))
        
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n\n"
        
        if text.strip():
            logger.info(f"Extracted {len(text)} characters using pypdf")
            return text.strip()
    except Exception as e:
        logger.warning(f"pypdf extraction failed: {e}")
    
    # Fallback to pdfplumber (better for complex layouts)
    try:
        import pdfplumber
        
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
        
        if text.strip():
            logger.info(f"Extracted {len(text)} characters using pdfplumber")
            return text.strip()
    except Exception as e:
        logger.warning(f"pdfplumber extraction failed: {e}")
    
    if not text.strip():
        logger.warning("PDF appears to be scanned/image-based. Manual review may be needed.")
        return "[Scanned PDF - Text extraction not available. Please ensure the PDF contains selectable text.]"
    
    return text.strip()


def extract_text_from_image(file_content: bytes) -> str:
    """
    Extract embedded text/metadata from images.
    Note: For actual OCR, external tools would be needed.
    This extracts any text metadata present in the image file.
    """
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
        
        image = Image.open(io.BytesIO(file_content))
        
        # Try to get any text metadata
        metadata_text = []
        
        # Check for EXIF data
        exif_data = image._getexif() if hasattr(image, '_getexif') and image._getexif() else {}
        if exif_data:
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                if isinstance(value, str):
                    metadata_text.append(f"{tag}: {value}")
        
        # Check image info
        if image.info:
            for key, value in image.info.items():
                if isinstance(value, str):
                    metadata_text.append(f"{key}: {value}")
        
        if metadata_text:
            text = "\n".join(metadata_text)
            logger.info(f"Extracted metadata from image: {len(text)} characters")
            return text
        
        logger.warning("Image contains no extractable text. OCR would be needed for scanned documents.")
        return "[Image file - Please ensure invoice data is provided as text or PDF with selectable text. For scanned images, manual entry may be required.]"
        
    except Exception as e:
        logger.error(f"Image processing failed: {e}")
        return f"[Error processing image: {str(e)}]"


def extract_text_from_text_file(file_content: bytes) -> str:
    """Extract text from plain text files"""
    try:
        # Try common encodings
        for encoding in ['utf-8', 'utf-16', 'latin-1', 'cp1252']:
            try:
                text = file_content.decode(encoding)
                logger.info(f"Decoded text file with {encoding}: {len(text)} characters")
                return text.strip()
            except UnicodeDecodeError:
                continue
        
        # Last resort: ignore errors
        text = file_content.decode('utf-8', errors='ignore')
        return text.strip()
        
    except Exception as e:
        logger.error(f"Text extraction failed: {e}")
        return f"[Error reading text file: {str(e)}]"


def detect_file_type(filename: str, file_content: bytes) -> str:
    """
    Detect file type from filename and content.
    Returns: 'pdf', 'image', or 'text'
    """
    filename_lower = filename.lower()
    
    # Check by extension first
    if filename_lower.endswith('.pdf'):
        return 'pdf'
    elif filename_lower.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp')):
        return 'image'
    elif filename_lower.endswith(('.txt', '.csv', '.json', '.xml')):
        return 'text'
    
    # Check by magic bytes
    if file_content[:4] == b'%PDF':
        return 'pdf'
    elif file_content[:8] == b'\x89PNG\r\n\x1a\n':
        return 'image'
    elif file_content[:2] in [b'\xff\xd8', b'GI']:  # JPEG, GIF
        return 'image'
    
    # Default to text
    return 'text'


def extract_text(filename: str, file_content: bytes) -> Tuple[str, str]:
    """
    Extract text from a file.
    
    Args:
        filename: Original filename
        file_content: File content as bytes
    
    Returns:
        Tuple of (extracted_text, file_type)
    """
    file_type = detect_file_type(filename, file_content)
    
    logger.info(f"Extracting text from {filename} (detected type: {file_type})")
    
    if file_type == 'pdf':
        text = extract_text_from_pdf(file_content)
    elif file_type == 'image':
        text = extract_text_from_image(file_content)
    else:
        text = extract_text_from_text_file(file_content)
    
    return text, file_type
