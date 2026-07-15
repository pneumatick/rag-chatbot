from enum import Enum, auto, unique
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
import chromadb

@unique
class Splitter(Enum):
    RECURSIVE = auto()

class VectorInterface():
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
                    docs_chunks.append(chunks)
                    for i, _ in enumerate(chunks):
                        chunk_ids.append(str(file_path.name) + str(i))

        return (docs_chunks, chunk_ids)

    def add_docs(self, dirname):
        (chunks, ids) = self._chunk_docs(dirname, Splitter.RECURSIVE)
        return (chunks, ids)