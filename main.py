from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import os
from dotenv import load_dotenv
from whoosh import index
from search import create_schema, index_documents, search_documents, get_all_documents, get_indexed_terms, get_document_terms
from logging_setup import logger

# Load environment variables
load_dotenv()

app = FastAPI(title="Document Searcher API")

# Get environment variables
doc_dir = os.getenv('DOC_DIR')
index_dir = os.getenv('INDEX_DIR')

# Create or open the index
schema = create_schema()
if not os.path.exists(index_dir):
    os.mkdir(index_dir)
    index_obj = index.create_in(index_dir, schema)
    logger.info("Indexing documents...")
    index_documents(index_obj, doc_dir, delete=True)
else:
    index_obj = index.open_dir(index_dir)
    logger.info("Opening existing index...")

class SearchQuery(BaseModel):
    query: str

class SearchResult(BaseModel):
    path: str
    filename: str
    highlights: str
    score: float
    language: str

@app.post("/search", response_model=List[SearchResult])
async def search(query: SearchQuery):
    results = search_documents(index_obj, query.query)
    if not results:
        raise HTTPException(status_code=404, detail="No results found")
    return results

@app.get("/documents", response_model=List[dict])
async def get_documents():
    return get_all_documents(index_obj)

@app.get("/terms/{field_name}")
async def get_terms(field_name: str):
    terms = get_indexed_terms(index_obj, field_name)
    if not terms:
        raise HTTPException(status_code=404, detail=f"No terms found for field: {field_name}")
    return terms

@app.get("/document_terms")
async def get_doc_terms(doc_path: str, field_name: str):
    terms = get_document_terms(index_obj, doc_path, field_name)
    if not terms:
        raise HTTPException(status_code=404, detail="No terms found for the specified document and field")
    return terms

@app.post("/reindex")
async def reindex():
    global index_obj
    index_documents(index_obj, doc_dir)
    return {"message": "Reindexing complete"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)