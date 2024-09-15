import os
from whoosh import index, fields, writing
from whoosh.analysis import RegexTokenizer, LowercaseFilter, StopFilter, CharsetFilter, StemmingAnalyzer
from whoosh.qparser import MultifieldParser
from whoosh.support.charset import default_charset, charset_table_to_dict
import PyPDF2
import docx
from docx.opc.constants import RELATIONSHIP_TYPE as RT
import openpyxl
from PIL import Image
import pytesseract
import io
import logging
import unicodedata
from dotenv import load_dotenv
from stemmers.slo import stem

# Load environment variables
load_dotenv()

def create_custom_analyzer():
    pattern = r'\w+|\d+|[^\w\s]+'
    my_analyzer = StemmingAnalyzer(expression=pattern, stemfn=stem)
    
    # Create a custom charset filter that preserves diacritical marks
    charset_table = charset_table_to_dict(default_charset)
    
    # Remove mappings for č, š, and ž to preserve them
    for char in 'čšžČŠŽ':
        charset_table.pop(ord(char), None)
    
    charset_filter = CharsetFilter(charset_table)
    
    # Create a custom analyzer
    custom_analyzer = (
        my_analyzer |
        charset_filter |
        LowercaseFilter() |
        StopFilter()
    )
    
    return custom_analyzer

def create_schema():
    custom_ana = create_custom_analyzer()
    return fields.Schema(
        path=fields.ID(stored=True),
        filename=fields.TEXT(stored=True, analyzer=custom_ana),
        extension=fields.TEXT(stored=True, analyzer=custom_ana),
        content=fields.TEXT(stored=True, analyzer=custom_ana)
    )

def create_index(schema, index_dir):
    if not os.path.exists(index_dir):
        os.mkdir(index_dir)
    return index.create_in(index_dir, schema)

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

def index_documents(index_obj, doc_dir, delete=False):
    writer = index_obj.writer()
    if delete:
        writer.commit(mergetype=writing.CLEAR)
        writer = index_obj.writer()
    for root, _, files in os.walk(doc_dir):
        for file in files:
            file_path = os.path.join(root, file)
            filename, extension = os.path.splitext(file)
            content = extract_text(file_path)
            if content:  # Only index if we successfully extracted content
                print(f"Indexing: {file_path}")
                #print(f"Content: {content[:50]}")
                #print(f"Filename: {filename}")
                
                # Normalize the text to NFC form
                normalized_content = unicodedata.normalize('NFC', content)
                normalized_filename = unicodedata.normalize('NFC', filename)
                
                writer.add_document(
                    path=file_path,
                    filename=normalized_filename,
                    extension=extension,
                    content=normalized_content
                )
    writer.commit()

def search_documents(index_obj, query_string):
    with index_obj.searcher() as searcher:
        query_parser = MultifieldParser(["filename", "extension", "content"], schema=index_obj.schema)
        query = query_parser.parse(query_string)
        results = searcher.search(query, limit=None)
        
        print(f"Number of results: {len(results)}")
        
        search_results = []
        for result in results:
            highlights = result.highlights("content") or result.highlights("filename") or result.highlights("extension") or "No highlights available"
            search_results.append({
                "path": result["path"],
                "filename": result["filename"] + result["extension"],
                "highlights": highlights,
                "score": result.score
            })
        
        return search_results

def main():
    doc_dir = os.getenv('DOC_DIR')
    index_dir = os.getenv('INDEX_DIR')
    
    schema = create_schema()
    if not os.path.exists(index_dir):
        os.mkdir(index_dir)
        index_obj = index.create_in(index_dir, schema)
        print("Indexing documents...")
        index_documents(index_obj, doc_dir)
        print("Indexing complete.")
    else:
        index_obj = index.create_in(index_dir, schema)
        # Re-index the documents with the new analyzer
        print("Re-indexing documents with updated analyzer...")
        index_documents(index_obj, doc_dir, True)
        print("Re-indexing complete.")
    
    while True:
        query = input("Enter your search query (or 'q' to quit): ")
        if query.lower() == 'q':
            break
        print(f"Searching for: {query}")
        results = search_documents(index_obj, query)
        if results:
            for result in results:
                print(f"File: {result['filename']}")
                print(f"Path: {result['path']}")
                print(f"Highlights: {result['highlights']}")
                print(f"Score: {result['score']:.2f}\n")
        else:
            print("No results found.")

if __name__ == "__main__":
    main()