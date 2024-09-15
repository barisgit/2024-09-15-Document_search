import os
from whoosh import index
from whoosh.fields import Schema, TEXT, ID, STORED
from whoosh.qparser import MultifieldParser
from whoosh.analysis import StemmingAnalyzer
from whoosh.query import Or
import PyPDF2
import docx
from docx.document import Document as DocxDocument
from docx.opc.constants import RELATIONSHIP_TYPE as RT
import openpyxl
from PIL import Image
import pytesseract
import io

def create_schema():
    stem_ana = StemmingAnalyzer()
    return Schema(
        path=ID(stored=True),
        filename=TEXT(stored=True, analyzer=stem_ana),
        content=TEXT(stored=True, analyzer=stem_ana)
    )

def create_index(schema, index_dir):
    if not os.path.exists(index_dir):
        os.mkdir(index_dir)
    return index.create_in(index_dir, schema)

def extract_text(file_path):
    _, ext = os.path.splitext(file_path.lower())
    if ext == '.pdf':
        return extract_pdf(file_path)
    elif ext in ['.docx', '.doc']:
        return extract_word(file_path)
    elif ext in ['.xlsx', '.xls']:
        return extract_excel(file_path)
    elif ext in ['.png', '.jpg', '.jpeg']:
        return extract_image(file_path)
    else:
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

def index_documents(index_obj, doc_dir):
    writer = index_obj.writer()
    for root, _, files in os.walk(doc_dir):
        for file in files:
            file_path = os.path.join(root, file)
            content = extract_text(file_path)
            if content:  # Only index if we successfully extracted content
                writer.add_document(
                    path=file_path,
                    filename=file,
                    content=content
                )
    writer.commit()

def search_documents(index_obj, query_string):
    try:
        with index_obj.searcher() as searcher:
            query_parser = MultifieldParser(["filename", "content"], schema=index_obj.schema)
            query = query_parser.parse(query_string)
            results = searcher.search(query, limit=None)
            
            print(f"Number of results: {len(results)}")  # Diagnostic print
            
            search_results = []
            for result in results:
                highlights = result.highlights("content") or result.highlights("filename") or "No highlights available"
                search_results.append({
                    "path": result["path"],
                    "filename": result["filename"],
                    "highlights": highlights,
                    "score": result.score
                })
            
            return search_results
    except Exception as e:
        print(f"An error occurred during search: {str(e)}")
        return []


def main():
    doc_dir = "/Users/blaz/Library/CloudStorage/OneDrive-Personal/Dokumenti/[01] Imported"
    index_dir = "./index"
    
    schema = create_schema()
    if not os.path.exists(index_dir):
        os.mkdir(index_dir)
        index_obj = index.create_in(index_dir, schema)
        print("Indexing documents...")
        index_documents(index_obj, doc_dir)
        print("Indexing complete.")
    else:
        index_obj = index.open_dir(index_dir)
    
    while True:
        query = input("Enter your search query (or 'q' to quit): ")
        if query.lower() == 'q':
            break
        print(f"Searching for: {query}")  # Diagnostic print
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