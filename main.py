import os
from whoosh import index, fields, writing
from whoosh.analysis import RegexTokenizer, LowercaseFilter, CharsetFilter, Token
from whoosh.qparser import MultifieldParser, OrGroup, QueryParser
from whoosh.analysis.morph import StemFilter
from whoosh.lang.porter import stem as english_stem
from whoosh.support.charset import default_charset, charset_table_to_dict
from whoosh.analysis.tokenizers import default_pattern
from whoosh.analysis.filters import StopFilter, STOP_WORDS
from whoosh.util.text import rcompile
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
from stemmers.slo import stem as slovenian_stem
from langdetect import detect

# Load environment variables
load_dotenv()

class MultiLingualStemFilter(StemFilter):
    def __init__(self, stemfn=None, ignore=None, cachesize=10000):
        self.stemfn = stemfn or self.stem
        self.ignore = frozenset(ignore) if ignore else frozenset()
        self.cachesize = cachesize
        # Initialize cache here
        self.cache = {}

    def stem(self, token):
        text = token.text
        try:
            lang = detect(text)
        except:
            lang = 'unknown'
        
        if lang == 'en':
            return english_stem(text)
        else:  # Default to English stemming for unknown languages
            return slovenian_stem(text)

    def __call__(self, tokens):
        # Ensure cache exists
        if not hasattr(self, 'cache'):
            self.cache = {}

        for t in tokens:
            text = t.text
            if text in self.ignore:
                yield t
            elif text in self.cache:
                t.text = self.cache[text]
                yield t
            else:
                stemmed = self.stemfn(t)
                if stemmed != text:
                    t.text = stemmed
                    if len(self.cache) < self.cachesize:
                        self.cache[text] = stemmed
                yield t

def MultiLingualAnalyzer(
    expression=r'\w+|\d+|[^\w\s]+',
    stoplist=STOP_WORDS,
    minsize=2,
    maxsize=None,
    gaps=False,
    ignore=None,
    cachesize=50000,
):
    """
    Composes a RegexTokenizer with a lower case filter, an optional stop
    filter, and a multi-lingual stemming filter.
    """
    ret = RegexTokenizer(expression=expression, gaps=True)
    chain = ret | LowercaseFilter()
    if stoplist is not None:
        chain = chain | StopFilter(stoplist=stoplist, minsize=minsize, maxsize=maxsize)
    return chain | MultiLingualStemFilter(ignore=ignore, cachesize=cachesize)

def create_schema():
    my_analyzer = RegexTokenizer() | LowercaseFilter() | StopFilter(stoplist=STOP_WORDS) | MultiLingualStemFilter()

    return fields.Schema(
        path=fields.ID(stored=True),
        filename=fields.TEXT(stored=True, analyzer=my_analyzer),
        extension=fields.TEXT(stored=True),
        content=fields.TEXT(stored=True, analyzer=my_analyzer),
        language=fields.TEXT(stored=True),
        time=fields.STORED
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
            if content:
                print(f"Indexing: {file_path}")
                
                # Detect language
                try:
                    lang = detect(content)
                except:
                    lang = 'unknown'
                    
                if lang == 'unknown':
                    try:
                        lang = detect(filename)
                    except:
                        lang = 'unknown'
                
                #print(f"Detected language: {lang}")
                
                # Normalize the text to NFC form
                normalized_content = unicodedata.normalize('NFC', content)
                normalized_filename = unicodedata.normalize('NFC', filename)
                
                writer.add_document(
                    path=file_path,
                    filename=normalized_filename,
                    extension=extension,
                    content=normalized_content,
                    language=lang
                )
    writer.commit()

def search_documents(index_obj, query_string):
    with index_obj.searcher() as searcher:
        # Use MultifieldParser to search in both content and filename
        fields = ["content", "filename"]
        query_parser = MultifieldParser(fields, schema=index_obj.schema)
        query = query_parser.parse(query_string)
                
        results = searcher.search(query, limit=None)
        
        print(f"Number of results: {len(results)}")
        
        search_results = []
        for result in results:
            # Try to get highlights from content first, then filename
            highlights = result.highlights("content") or result.highlights("filename") or "No highlights available"
            search_results.append({
                "path": result["path"],
                "filename": result["filename"] + result["extension"],
                "highlights": highlights,
                "score": result.score,
                "language": result["language"]
            })
        
        return search_results

def incremental_index(index_obj, doc_dir):
    writer = index_obj.writer()

    # The set of all paths in the index
    indexed_paths = set()
    # The set of all paths we need to re-index
    to_index = set()

    with index_obj.searcher() as searcher:
        # Loop over the stored fields in the index
        for fields in searcher.all_stored_fields():
            indexed_path = fields['path']
            indexed_paths.add(indexed_path)

            if not os.path.exists(indexed_path):
                # This file was deleted since it was indexed
                writer.delete_by_term('path', indexed_path)
            else:
                # Check if this file was changed since it was indexed
                indexed_time = fields.get('time')
                if indexed_time:
                    mtime = os.path.getmtime(indexed_path)
                    if mtime > indexed_time:
                        # The file has changed, delete it and add it to the list of
                        # files to reindex
                        writer.delete_by_term('path', indexed_path)
                        to_index.add(indexed_path)

        # Loop over the files in the filesystem
        for root, _, files in os.walk(doc_dir):
            for file in files:
                path = os.path.join(root, file)
                if path in to_index or path not in indexed_paths:
                    # This is either a file that's changed, or a new file
                    # that wasn't indexed before. So index it!
                    print(f"Indexing: {path}")
                    index_document(writer, path)

    writer.commit()

def index_document(writer, file_path):
    filename, extension = os.path.splitext(os.path.basename(file_path))
    try:
        content = extract_text(file_path)
        if content:
            try:
                lang = detect(content)
            except:
                lang = detect(filename) if filename else 'unknown'
            
            normalized_content = unicodedata.normalize('NFC', content)
            normalized_filename = unicodedata.normalize('NFC', filename)
            
            writer.add_document(
                path=file_path,
                filename=normalized_filename,
                extension=extension,
                content=normalized_content,
                language=lang,
                time=os.path.getmtime(file_path)
            )
            print(f"Successfully indexed: {file_path}")
        else:
            print(f"No content extracted from: {file_path}")
    except Exception as e:
        print(f"Error indexing {file_path}: {str(e)}")
        logging.error(f"Error indexing {file_path}: {str(e)}", exc_info=True)

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
        index_obj = index.open_dir(index_dir)
        print("Incrementally indexing documents...")
        incremental_index(index_obj, doc_dir)
        print("Incremental indexing complete.")
    
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
                print(f"Language: {result['language']}")
                print(f"Highlights: {result['highlights']}")
                print(f"Score: {result['score']:.2f}\n")
        else:
            print("No results found.")

if __name__ == "__main__":
    main()