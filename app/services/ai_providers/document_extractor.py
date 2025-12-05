"""
Document and URL text extraction for EDEN Asset Library AI extraction.

This module provides utilities to extract text content from:
- PDF files
- Text files (.txt, .md)
- HTML from product URLs

CAD/3D files (DWG, DXF, STEP, STL, OBJ) are not parsed in v1 - they are
listed as "uploaded but not parsed" in the extraction context.
"""

import io
import logging
import re
from typing import List, Optional, Tuple

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# File extensions we can extract text from
TEXT_EXTRACTABLE_EXTENSIONS = {'.pdf', '.txt', '.md', '.text'}

# File extensions we skip (CAD/3D files)
SKIPPED_EXTENSIONS = {'.dwg', '.dxf', '.step', '.stp', '.iges', '.igs', '.stl', '.obj'}

# Maximum file size to attempt extraction (10MB)
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024

# Timeout for URL fetching
URL_FETCH_TIMEOUT = 15.0


def get_file_extension(filename: str) -> str:
    """Get lowercase file extension from filename."""
    if '.' not in filename:
        return ''
    return '.' + filename.rsplit('.', 1)[-1].lower()


def can_extract_text(filename: str) -> bool:
    """Check if we can extract text from this file type."""
    ext = get_file_extension(filename)
    return ext in TEXT_EXTRACTABLE_EXTENSIONS


def is_skipped_file(filename: str) -> bool:
    """Check if this file type is intentionally skipped (CAD/3D)."""
    ext = get_file_extension(filename)
    return ext in SKIPPED_EXTENSIONS


async def extract_text_from_pdf(content: bytes, filename: str) -> str:
    """
    Extract text from a PDF file.
    
    Args:
        content: The PDF file content as bytes
        filename: The filename (for logging)
        
    Returns:
        Extracted text from the PDF
    """
    try:
        from pypdf import PdfReader
        
        pdf_file = io.BytesIO(content)
        reader = PdfReader(pdf_file)
        
        text_parts = []
        for i, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"[Page {i + 1}]\n{page_text}")
            except Exception as e:
                logger.warning(f"Failed to extract text from page {i + 1} of {filename}: {e}")
                continue
        
        full_text = "\n\n".join(text_parts)
        logger.info(f"Extracted {len(full_text)} characters from PDF: {filename}")
        return full_text
        
    except Exception as e:
        logger.error(f"Failed to extract text from PDF {filename}: {e}")
        return ""


async def extract_text_from_text_file(content: bytes, filename: str) -> str:
    """
    Extract text from a plain text file.
    
    Args:
        content: The file content as bytes
        filename: The filename (for logging)
        
    Returns:
        The text content
    """
    try:
        # Try UTF-8 first, then fall back to latin-1
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            text = content.decode('latin-1')
        
        logger.info(f"Extracted {len(text)} characters from text file: {filename}")
        return text
        
    except Exception as e:
        logger.error(f"Failed to extract text from {filename}: {e}")
        return ""


async def fetch_file_content(url: str) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Fetch file content from a URL.
    
    Args:
        url: The URL to fetch
        
    Returns:
        Tuple of (content bytes, error message if any)
    """
    try:
        async with httpx.AsyncClient(timeout=URL_FETCH_TIMEOUT, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            # Check file size
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > MAX_FILE_SIZE_BYTES:
                return None, f"File too large: {content_length} bytes"
            
            return response.content, None
            
    except httpx.TimeoutException:
        return None, f"Timeout fetching {url}"
    except httpx.HTTPStatusError as e:
        return None, f"HTTP error {e.response.status_code} fetching {url}"
    except Exception as e:
        return None, f"Error fetching {url}: {str(e)}"


async def extract_text_from_file(url: str, filename: str) -> Tuple[str, Optional[str]]:
    """
    Extract text from a file given its URL and filename.
    
    Args:
        url: The URL to fetch the file from
        filename: The filename (used to determine file type)
        
    Returns:
        Tuple of (extracted text, error message if any)
    """
    ext = get_file_extension(filename)
    
    # Check if this is a skipped file type
    if is_skipped_file(filename):
        return "", f"Skipped CAD/3D file: {filename}"
    
    # Check if we can extract text
    if not can_extract_text(filename):
        return "", f"Unsupported file type: {filename}"
    
    # Fetch the file content
    content, error = await fetch_file_content(url)
    if error:
        return "", error
    
    if not content:
        return "", f"Empty content from {filename}"
    
    # Extract text based on file type
    if ext == '.pdf':
        text = await extract_text_from_pdf(content, filename)
    else:
        text = await extract_text_from_text_file(content, filename)
    
    return text, None


async def extract_text_from_url(url: str) -> Tuple[str, Optional[str]]:
    """
    Extract text content from a webpage URL.
    
    Args:
        url: The webpage URL to fetch and parse
        
    Returns:
        Tuple of (extracted text, error message if any)
    """
    try:
        logger.info(f"Starting URL text extraction for: {url}")
        
        async with httpx.AsyncClient(
            timeout=URL_FETCH_TIMEOUT, 
            follow_redirects=True,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            html_content = response.text
            logger.info(f"Fetched {len(html_content)} bytes of HTML from {url}")
            
            # Parse HTML and extract text
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Log the page title for debugging
            title_tag = soup.find('title')
            page_title = title_tag.get_text(strip=True) if title_tag else "No title"
            logger.info(f"Page title: {page_title}")
            
            # Remove script, style, and navigation elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript', 'iframe']):
                element.decompose()
            
            # Try multiple strategies to find product content
            text_parts = []
            
            # Strategy 1: Look for product-specific containers (common in e-commerce)
            product_selectors = [
                # Common product page selectors
                {'class_': re.compile(r'product[-_]?(description|info|details|content|summary)', re.I)},
                {'class_': re.compile(r'(description|details|specs|specifications)[-_]?(content|text|body)?', re.I)},
                {'id': re.compile(r'product[-_]?(description|info|details|content)', re.I)},
                {'id': re.compile(r'(description|details|specs|specifications)', re.I)},
                # Shopify-specific selectors
                {'class_': 'product-single__description'},
                {'class_': 'product__description'},
                {'class_': 'product-description'},
                # Generic content selectors
                {'class_': re.compile(r'(main[-_]?content|content[-_]?area|page[-_]?content)', re.I)},
                {'itemprop': 'description'},
            ]
            
            for selector in product_selectors:
                elements = soup.find_all(**selector)
                for elem in elements:
                    elem_text = elem.get_text(separator='\n', strip=True)
                    if elem_text and len(elem_text) > 50:  # Only include substantial text
                        text_parts.append(elem_text)
                        logger.info(f"Found product content with selector {selector}: {len(elem_text)} chars")
            
            # Strategy 2: Look for structured data (JSON-LD)
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_ld_scripts:
                try:
                    import json
                    data = json.loads(script.string)
                    # Handle both single objects and arrays
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if isinstance(item, dict):
                            # Extract product description from structured data
                            if item.get('@type') == 'Product' or 'Product' in str(item.get('@type', '')):
                                desc = item.get('description', '')
                                if desc:
                                    text_parts.append(f"Product Description: {desc}")
                                    logger.info(f"Found JSON-LD product description: {len(desc)} chars")
                                name = item.get('name', '')
                                if name:
                                    text_parts.append(f"Product Name: {name}")
                except (json.JSONDecodeError, TypeError) as e:
                    logger.debug(f"Could not parse JSON-LD: {e}")
            
            # Strategy 3: Look for meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                meta_content = meta_desc.get('content', '')
                if meta_content and len(meta_content) > 20:
                    text_parts.append(f"Page Description: {meta_content}")
                    logger.info(f"Found meta description: {len(meta_content)} chars")
            
            # Strategy 4: Fall back to main content areas
            if not text_parts:
                logger.info("No product-specific content found, falling back to main content areas")
                main_content = soup.find('main') or soup.find('article') or soup.find('body')
                
                if main_content:
                    # Get text and clean it up
                    text = main_content.get_text(separator='\n', strip=True)
                    if text:
                        text_parts.append(text)
                        logger.info(f"Found main content: {len(text)} chars")
            
            # Combine all text parts
            if text_parts:
                # Remove duplicates while preserving order
                seen = set()
                unique_parts = []
                for part in text_parts:
                    # Normalize for comparison
                    normalized = part.strip().lower()[:100]
                    if normalized not in seen:
                        seen.add(normalized)
                        unique_parts.append(part)
                
                combined_text = "\n\n".join(unique_parts)
                
                # Clean up excessive whitespace
                combined_text = re.sub(r'\n{3,}', '\n\n', combined_text)
                combined_text = re.sub(r' {2,}', ' ', combined_text)
                
                # Limit to reasonable size (20k chars)
                if len(combined_text) > 20000:
                    combined_text = combined_text[:20000] + "\n[... truncated ...]"
                
                logger.info(f"Successfully extracted {len(combined_text)} characters from URL: {url}")
                return combined_text, None
            else:
                logger.warning(f"No extractable content found at {url}")
                return "", f"No extractable content found at {url}"
                
    except httpx.TimeoutException:
        logger.error(f"Timeout fetching URL: {url}")
        return "", f"Timeout fetching {url}"
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error {e.response.status_code} fetching URL: {url}")
        return "", f"HTTP error {e.response.status_code} fetching {url}"
    except Exception as e:
        logger.error(f"Error extracting text from URL {url}: {e}", exc_info=True)
        return "", f"Error extracting text from {url}: {str(e)}"


async def extract_all_document_text(
    documents: List[dict],
    max_total_chars: int = 20000
) -> Tuple[str, List[str], List[str]]:
    """
    Extract text from all provided documents.
    
    Args:
        documents: List of document dicts with 'url' and 'filename' keys
        max_total_chars: Maximum total characters to return
        
    Returns:
        Tuple of (concatenated text, list of processed files, list of skipped files)
    """
    all_text_parts = []
    processed_files = []
    skipped_files = []
    total_chars = 0
    
    for doc in documents:
        url = doc.get('url', '')
        filename = doc.get('filename', '')
        
        if not url or not filename:
            continue
        
        # Check if we've hit the character limit
        if total_chars >= max_total_chars:
            skipped_files.append(f"{filename} (character limit reached)")
            continue
        
        text, error = await extract_text_from_file(url, filename)
        
        if error:
            skipped_files.append(f"{filename} ({error})")
            continue
        
        if text:
            # Truncate if needed to stay within limit
            remaining_chars = max_total_chars - total_chars
            if len(text) > remaining_chars:
                text = text[:remaining_chars] + "\n[... truncated ...]"
            
            all_text_parts.append(f"\n--- Document: {filename} ---\n{text}")
            processed_files.append(filename)
            total_chars += len(text)
    
    combined_text = "\n".join(all_text_parts)
    return combined_text, processed_files, skipped_files
