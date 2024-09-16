import os
import PyPDF2
import docx
from docx.opc.constants import RELATIONSHIP_TYPE as RT
import openpyxl
from PIL import Image
import pytesseract
import io
import logging
import unicodedata

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
        '.jpeg': extract_image
    }
    
    extract_func = extraction_functions.get(ext)
    
    if extract_func:
        try:
            text = extract_func(file_path)
            # Normalize the extracted text to NFC form
            return unicodedata.normalize('NFC', text)
        except Exception as e:
            logging.error(f"Error extracting text from {file_path}: {str(e)}")
    else:
        logging.warning(f"Unsupported file type: {ext} for file {file_path}")
    
    return ''

def extract_pdf(file_path):
    text = ""
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text

def extract_word(file_path):
    doc = docx.Document(file_path)
    text = " ".join([paragraph.text for paragraph in doc.paragraphs])
    
    # Extract text from images in the Word document
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
        for row in sheet.iter_rows(values_only=True):
            text += " ".join([str(cell) for cell in row if cell is not None]) + "\n"
    return text

def extract_image(file_path):
    return pytesseract.image_to_string(Image.open(file_path))