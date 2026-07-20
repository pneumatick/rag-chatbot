from enum import Enum, auto, unique
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from chromadb import HttpClient as ChromadbHttpClient
from openai import OpenAI

lm_studio_client = OpenAI(
    base_url="http://host.docker.internal:1234/v1",
    api_key="lm-studio"  # required by the client, but LM Studio ignores it"
)

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

        return len(chunks)

    def _retrieve(self, query, k=5):
        results = self.collection.query(
            query_texts=[query],
            n_results=k
        )

        return results["documents"][0]  # list of chunk texts

    def query(self, user_query):
        # Get results from querying the chunked data in chromadb
        results = self._retrieve(user_query)

        # Flatten the results into a single context block
        context = "\n---\n".join(results)

        # Synthesis prompt for the LLM
        system_prompt = (
            "You are an insightful research assistant analyzing the user's personal writings. "
            "Your goal is to synthesize the provided context and find deep, non-obvious connections "
            "between the concepts requested. Do not invent facts; rely strictly on the text provided."
        )

        user_prompt = f"""
            Based on the following excerpts from my writings, answer this question:
            "{user_query}"

            ---
            WRITING EXCERPTS:
            {context}
            ---

            Provide a structured analysis highlighting the primary intersections, tensions, or patterns you see.
         """

        # Prompt the LLM
        response = lm_studio_client.chat.completions.create(
            model="local-model", # LM Studio ignores this if only one model is loaded, but pass it anyway
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            #stream=True
        )

        return {
            "answer": response.choices[0].message.content,
            "sources": results,
        }
