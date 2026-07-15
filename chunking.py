from langchain_text_splitters import RecursiveCharacterTextSplitter
from enum import Enum, auto, unique
from pathlib import Path

@unique
class Splitter(Enum):
    RECURSIVE = auto()

def get_splitter(type):
    if type == Splitter.RECURSIVE:
        return RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=0)
    else:
        return None

def chunk_doc(document, split_type):
    splitter = get_splitter(split_type)

    if not splitter:
        return "Unknown splitter selected"
    
    chunks = splitter.split_text(document)

    return chunks

def chunk_docs(split_type):
    path = Path("user-docs")
    docs_string = []
    for file_path in path.iterdir():
        if file_path.is_file():
            with open(file_path, "r", encoding="utf-8") as file:
                docs_string.append(chunk_doc(file.read(), split_type))

    return docs_string