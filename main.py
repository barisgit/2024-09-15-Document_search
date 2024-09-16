import os
from whoosh import index, fields, writing
from dotenv import load_dotenv
from analyzer import MultiLingualAnalyzer
from search import index_documents, search_documents

# Load environment variables
load_dotenv()

def create_schema():
    my_analyzer = MultiLingualAnalyzer()

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

def main():
    doc_dir = os.getenv('DOC_DIR')
    index_dir = os.getenv('INDEX_DIR')
    
    schema = create_schema()
    if not os.path.exists(index_dir):
        os.mkdir(index_dir)
        index_obj = index.create_in(index_dir, schema)
        print("Indexing documents...")
        index_documents(index_obj, doc_dir, delete=True)
    else:
        index_obj = index.open_dir(index_dir)
        print("Updating index...")
        index_documents(index_obj, doc_dir)
    
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