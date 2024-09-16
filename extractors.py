import os
import PyPDF2
import docx
from docx.opc.constants import RELATIONSHIP_TYPE as RT
import openpyxl
from PIL import Image
import pytesseract
import io
import unicodedata
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import mobi
from logging_setup import logger

def extract_text(file_path: str) -> str:
    _, ext = os.path.splitext(file_path.lower())
    extraction_functions = {
        '.pdf': extract_pdf,
        '.docx': extract_word,
        '.doc': extract_word,
        '.xlsx': extract_excel,
        '.xls': extract_excel,
        '.png': extract_image,
        '.jpg': extract_image,
        '.jpeg': extract_image,
        #'.mobi': extract_mobi, # DOESN'T WORK YET
        '.epub': extract_epub
    }
    extract_func = extraction_functions.get(ext)
    if extract_func:
        with ThreadPoolExecutor() as executor:
            future = executor.submit(extract_func, file_path)
            try:
                text = future.result(timeout=10.0)  # 10 seconds timeout
                return unicodedata.normalize('NFC', text)
            except TimeoutError:
                logger.error(f"Timeout extracting text from {file_path}")
            except Exception as e:
                logger.error(f"Error extracting text from {file_path}: {str(e)}")
    else:
        logger.warning(f"Unsupported file type: {ext} for file {file_path}")
    return ''

def extract_pdf(file_path):
    text = ""
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for i, page in enumerate(reader.pages):
            if i > 250:
                break
            text += page.extract_text() + "\n"
    return text

def extract_word(file_path):
    doc = docx.Document(file_path)
    text = " ".join([paragraph.text for paragraph in doc.paragraphs])
    image_text = ""
    for rel in doc.part.rels.values():
        if rel.reltype == RT.IMAGE:
            image_stream = rel.target_part.blob
            image = Image.open(io.BytesIO(image_stream))
            image_text += pytesseract.image_to_string(image) + " "
    return text + " " + image_text

def extract_excel(file_path):
    wb = openpyxl.load_workbook(file_path, data_only=True)
    text = ""
    for sheet in wb:
        for i, row in enumerate(sheet.iter_rows(values_only=True)):
            if i > 1000:
                break
            text += " ".join([str(cell) for cell in row if cell is not None]) + "\n"
    return text

def extract_image(file_path):
    return pytesseract.image_to_string(Image.open(file_path))

def extract_mobi(file_path):
    try:
        extraction_result = mobi.extract(file_path)
        
        if isinstance(extraction_result, tuple):
            extracted_path = extraction_result[1]
        else:
            extracted_path = extraction_result

        text_buffer = io.StringIO()
        
        for root, dirs, files in os.walk(extracted_path):
            for file in files:
                if file.endswith('.html') or file.endswith('.htm'):
                    with open(os.path.join(root, file), 'r', encoding='utf-8', errors='ignore') as f:
                        soup = BeautifulSoup(f, 'html.parser')
                        text_buffer.write(soup.get_text() + "\n")
        
        text = text_buffer.getvalue()
        logger.debug(f"Extracted text from MOBI: {text[:100]}...")
        return text
    except Exception as e:
        logger.error(f"Error extracting MOBI file {file_path}: {str(e)}")
        return ""
    finally:
        # Clean up extracted files if they exist
        if 'extracted_path' in locals():
            for root, dirs, files in os.walk(extracted_path, topdown=False):
                for file in files:
                    os.remove(os.path.join(root, file))
                for dir in dirs:
                    os.rmdir(os.path.join(root, dir))
            os.rmdir(extracted_path)

def extract_epub(file_path):
    try:
        book = epub.read_epub(file_path)
        text = ""
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_content(), 'html.parser')
                text += soup.get_text() + "\n"
        logger.debug(f"Extracted text from EPUB: {text[:100]}...")
        return text
    except Exception as e:
        logger.error(f"Error extracting EPUB file {file_path}: {str(e)}")
        return ""

def sanitize_filename(filename):
    return ''.join(c for c in filename if c.isalnum() or c in ('-', '_')).rstrip()

def process_files(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            logger.info(f"Indexing: {file_path}")
        
            text = extract_text(file_path)
            
            if not text:
                logger.warning(f"No content extracted from: {file_path}")
            else:
                output_filename = sanitize_filename(os.path.splitext(file)[0]) + ".txt"
                output_path = os.path.join(root, output_filename)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                logger.info(f"Extracted text saved to: {output_path}")