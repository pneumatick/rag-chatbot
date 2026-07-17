from enum import Enum, auto, unique
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from chromadb import HttpClient as ChromadbHttpClient

@unique
class Splitter(Enum):
    RECURSIVE = auto()

class VectorInterface():
    def __init__(self, client=None):
        self.client = client if client else self._init_client()
        self.collection = self._get_collection("user-docs-collection")
    
    def _init_client(self):
        return ChromadbHttpClient(host="localhost", port=8000)

    def _get_collection(self, name):
        return self.client.get_or_create_collection(name=name)

    def _get_splitter(self, type):
        if type == Splitter.RECURSIVE:
            return RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=0)
        else:
            return None

    def _chunk_doc(self, document, split_type):
        splitter = self._get_splitter(split_type)

        # NOTE: Handle error properly
        if not splitter:
            return "Unknown splitter selected"
        
        chunks = splitter.split_text(document)

        return chunks

    def _chunk_docs(self, dirname, split_type):
        path = Path(dirname)
        docs_chunks = []
        chunk_ids = []
        for file_path in path.iterdir():
            if file_path.is_file():
                with open(file_path, "r", encoding="utf-8") as file:
                    chunks = self._chunk_doc(file.read(), split_type)
                    for i, chunk in enumerate(chunks):
                        docs_chunks.append(chunk)
                        chunk_ids.append(str(file_path.name) + str(i))

        return (docs_chunks, chunk_ids)

    def add_docs(self, dirname):
        # Perform document chunking
        (chunks, ids) = self._chunk_docs(dirname, Splitter.RECURSIVE)

        self.collection.add(
            ids=ids,
            documents=chunks
        )
    
    def retrieve(self, query, k=5):
        results = self.collection.query(
            query_texts=[query],
            n_results=k
        )

        return results["documents"][0]  # list of chunk texts