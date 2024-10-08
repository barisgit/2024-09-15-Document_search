import os
from whoosh import index, fields, writing
from whoosh.qparser import MultifieldParser
from langdetect import detect
from extractors import extract_text, audio_files_queue, process_audio_queue
import unicodedata
from analyzer import MultiLingualAnalyzer
from logging_setup import logger

def create_schema():
    my_analyzer = MultiLingualAnalyzer()

    return fields.Schema(
        path=fields.ID(stored=True, unique=True, sortable=True),
        filename=fields.TEXT(stored=True, analyzer=my_analyzer),
        extension=fields.TEXT(stored=True),
        content=fields.TEXT(stored=True, analyzer=my_analyzer),
        language=fields.TEXT(stored=True),
        skipped=fields.BOOLEAN(stored=True),
        time=fields.STORED
    )

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
                    skipped = False
                    if not content:
                        skipped = True
                        
                    logger.info(f"Indexing: {file}")
                    
                    try:
                        lang = detect(content)
                    except:
                        try:
                            lang = detect(filename)
                        except:
                            lang = 'unknown'
                    
                    normalized_content = unicodedata.normalize('NFC', content)
                    normalized_filename = unicodedata.normalize('NFC', filename)
                    
                    logger.debug(f"Adding document: {normalized_filename}{extension}")
                    logger.debug(f"Language: {lang}")
                    logger.debug(f"Content: {normalized_content[:100]}...")
                    
                    writer.add_document(
                        path=file_path,
                        filename=normalized_filename,
                        extension=extension,
                        content=normalized_content,
                        language=lang,
                        skipped=skipped,
                        time=os.path.getmtime(file_path)
                    )

    logger.info("Audio files queue: {}".format(audio_files_queue))
    
    # Process audio files in the queue
    while audio_files_queue:
        results = process_audio_queue()
        with index_obj.writer() as writer:
            for file_path, text in results.items():
                logger.debug(f"Processed {file_path}: {text[:100]}...")
                filename, extension = os.path.splitext(os.path.basename(file_path))
                normalized_content = unicodedata.normalize('NFC', text)
                normalized_filename = unicodedata.normalize('NFC', filename)
                try:
                    lang = detect(text)
                except:
                    lang = 'unknown'
                
                writer.update_document(
                    path=file_path,
                    filename=normalized_filename,
                    extension=extension,
                    content=normalized_content,
                    language=lang,
                    skipped=False,
                    time=os.path.getmtime(file_path)
                )
            
    logger.info("Indexing complete.")

def search_documents(index_obj, query_string):
    with index_obj.searcher() as searcher:
        fields = ["content", "filename"]
        query_parser = MultifieldParser(fields, schema=index_obj.schema)
        query = query_parser.parse(query_string)
                
        results = searcher.search(query, limit=None)
        
        logger.info(f"Number of results: {len(results)}")
        
        search_results = []
        for result in results:
            highlights = result.highlights("content") or result.highlights("filename") or "No highlights available"
            search_results.append({
                "path": result["path"],
                "filename": result["filename"] + result["extension"],
                "highlights": highlights,
                "score": result.score,
                "language": result["language"]
            })
        
        return search_results
    
def get_all_documents(index_obj):
    with index_obj.searcher() as searcher:
        return [dict(doc) for doc in searcher.all_stored_fields()]

def get_indexed_terms(index_obj, field_name):
    with index_obj.searcher() as searcher:
        return list(searcher.lexicon(field_name))

def get_document_terms(index_obj, doc_path, field_name):
    with index_obj.searcher() as searcher:
        doc = searcher.document(path=doc_path)
        if doc and field_name in doc:
            content = doc[field_name]
            analyzer = index_obj.schema[field_name].analyzer
            return [token.text for token in analyzer(content)]
    return []