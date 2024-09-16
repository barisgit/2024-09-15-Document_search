import os
from whoosh import index, fields, writing
from whoosh.qparser import MultifieldParser
from whoosh.util.text import rcompile
from langdetect import detect
from extractors import extract_text
import unicodedata

def index_documents(index_obj, doc_dir, delete=False):
    if delete:
        writer = index_obj.writer()
        writer.commit(mergetype=writing.CLEAR)

    indexed_paths = set()
    to_index = set()

    # Check existing documents in the index
    with index_obj.searcher() as searcher:
        for fields in searcher.all_stored_fields():
            indexed_path = fields['path']
            indexed_paths.add(indexed_path)

            if not os.path.exists(indexed_path):
                with index_obj.writer() as writer:
                    writer.delete_by_term('path', indexed_path)
            else:
                indexed_time = fields.get('time')
                if indexed_time:
                    mtime = os.path.getmtime(indexed_path)
                    if mtime > indexed_time:
                        with index_obj.writer() as writer:
                            writer.delete_by_term('path', indexed_path)
                        to_index.add(indexed_path)

    # Index new or updated documents
    with index_obj.writer() as writer:
        for root, _, files in os.walk(doc_dir):
            for file in files:
                file_path = os.path.join(root, file)
                if file_path in to_index or file_path not in indexed_paths:
                    filename, extension = os.path.splitext(file)
                    content = extract_text(file_path)
                    if content:
                        print(f"Indexing: {file_path}")
                        
                        try:
                            lang = detect(content)
                        except:
                            try:
                                lang = detect(filename)
                            except:
                                lang = 'unknown'
                        
                        normalized_content = unicodedata.normalize('NFC', content)
                        normalized_filename = unicodedata.normalize('NFC', filename)
                        
                        if False:
                            print(f"Adding document: {normalized_filename}{extension}")
                            print(f"Language: {lang}")
                            print(f"Content: {normalized_content[:100]}...")
                            print("--------------------")
                        
                        writer.add_document(
                            path=file_path,
                            filename=normalized_filename,
                            extension=extension,
                            content=normalized_content,
                            language=lang,
                            time=os.path.getmtime(file_path)
                        )
                    else:
                        print(f"No content extracted from: {file_path}")

    print("Indexing complete.")

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