from enum import Enum, auto, unique
from pathlib import Path
import json
from langchain_text_splitters import RecursiveCharacterTextSplitter
from chromadb import HttpClient as ChromadbHttpClient
from langchain_chroma import Chroma
from openai import OpenAI
from flask import Response

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
        self.collection = self._get_collection("user-docs-collection") # NOTE: Rename from collection to something describing VectorStore
        self.retriever = self.collection.as_retriever(
            search_type="similarity_score_threshold",
            search_kwargs={"k": 5, "score_threshold": 0.2}
        )

    def _init_client(self):
        return ChromadbHttpClient(host="localhost", port=8000)

    def _get_collection(self, name):
        #return self.client.get_or_create_collection(name=name)
        return Chroma(
            collection_name=name,
            #embedding_fuction=CUSTOM_EMBEDDING_FUNC
            host="localhost",
            port=8000
        )

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

        self.collection.add_texts(
            ids=ids, # NOTE: Consider either changing ID method or using defaults
            documents=chunks
        )

        return len(chunks)

    def _retrieve(self, query, k=5):
        results = self.retriever.invoke(
            input=query
        )

        return results

    def query(self, user_query):
        # Get results from querying the chunked data in chromadb
        results = self._retrieve(user_query)["documents"][0]  # list of chunk texts

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
            temperature=0.3
        )

        return {
            "answer": response.choices[0].message.content,
            "sources": results,
        }

    def query_stream(self, user_query):
        """Stream response chunks from the LLM as Server-Sent Events."""
        results = self._retrieve(user_query, k=10)["documents"][0]  # list of chunk texts
        
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
            {"---\n".join(results)}
            ---

            Provide a structured analysis highlighting the primary intersections, tensions, or patterns you see.
         """

        response = lm_studio_client.chat.completions.create(
            model="local-model",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            stream=True
        )

        def generate():
            yield f"data: {{\"event\": \"started\", \"message\": \"Analyzing your writings...\", \"sources\": {json.dumps(results)}}}\n\n"
            
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
                    yield f"data: {{\"event\": \"chunk\", \"message\": \"{content}\"}}\n\n"
                elif chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.reasoning_content:
                    reasoning_content = chunk.choices[0].delta.reasoning_content.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
                    yield f"data: {{\"event\": \"reasoning\", \"message\": \"{reasoning_content}\"}}\n\n"
            
            yield "data: {\"event\": \"completed\", \"message\": \"Analysis complete.\"}\n\n"

        return generate()


def sse_response(stream):
    """Helper to convert a generator into an SSE Response."""
    def generate():
        for data in stream:
            yield f"{data}\n\n".encode()
    
    return Response(generate(), mimetype="text/event-stream")