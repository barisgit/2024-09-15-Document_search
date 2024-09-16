import os
from whoosh import index, fields, writing
from dotenv import load_dotenv
from search import index_documents, search_documents, create_schema, get_all_documents, get_indexed_terms, get_document_terms
from logging_setup import logger

# Load environment variables
load_dotenv()

def main():
    doc_dir = os.getenv('DOC_DIR')
    logger.info(f"Document directory: {doc_dir}")
    index_dir = os.getenv('INDEX_DIR')
    
    schema = create_schema()
    if not os.path.exists(index_dir):
        os.mkdir(index_dir)
        index_obj = index.create_in(index_dir, schema)
        logger.info("Indexing documents...")
        index_documents(index_obj, doc_dir, delete=True)
    else:
        index_obj = index.open_dir(index_dir)
        logger.info("Updating index...")
        index_documents(index_obj, doc_dir)
    
    while True:
        logger.info("\nOptions:")
        logger.info("1. Search documents")
        logger.info("2. View index contents")
        logger.info("3. View all indexed terms")
        logger.info("4. View terms for a specific document")
        logger.info("5. Quit")
        choice = input("Enter your choice (1-5): ")
        
        if choice == '1':
            query = input("Enter your search query: ")
            logger.info(f"Searching for: {query}")
            results = search_documents(index_obj, query)
            if results:
                for result in results:
                    logger.info(f"File: {result['filename']}")
                    logger.info(f"Path: {result['path']}")
                    logger.info(f"Language: {result['language']}")
                    logger.info(f"Highlights: {result['highlights']}")
                    logger.info(f"Score: {result['score']:.2f}\n")
            else:
                logger.warning("No results found.")
        elif choice == '2':
            logger.info("Index contents:")
            documents = get_all_documents(index_obj)
            for doc in documents:
                logger.info(f"Path: {doc['path']}")
                logger.info(f"Filename: {doc['filename']}{doc['extension']}")
                logger.info(f"Language: {doc['language']}")
                logger.info(f"Skipped: {doc['skipped']}")
                logger.info(f"Time: {doc['time']}")
                logger.info("--------------------")
        elif choice == '3':
            field = input("Enter field name to view terms (e.g., 'content' or 'filename'): ")
            terms = get_indexed_terms(index_obj, field)
            logger.info(f"Indexed terms for field '{field}':")
            for term in terms:
                logger.info(term)
        elif choice == '4':
            documents = get_all_documents(index_obj)
            for i, doc in enumerate(documents):
                logger.info(f"{i+1}. {doc['filename']}{doc['extension']}")
            try:
                doc_choice = int(input("Enter the number of the document to view terms for: ")) - 1
                if doc_choice < 0 or doc_choice >= len(documents):
                    raise ValueError("Invalid document number")
                field = input("Enter field name to view terms (e.g., 'content' or 'filename'): ")
                terms = get_document_terms(index_obj, documents[doc_choice]['path'], field)
                if terms:
                    logger.info(f"Terms for document '{documents[doc_choice]['filename']}{documents[doc_choice]['extension']}' in field '{field}':")
                    for term in terms:
                        logger.info(term)
                else:
                    logger.warning(f"No terms found for the specified document and field.")
            except ValueError as e:
                logger.error(f"Error: {str(e)}")
            except Exception as e:
                logger.error(f"An error occurred: {str(e)}")
        elif choice == '5':
            break
        else:
            logger.warning("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()