import json
from typing import Sequence
from openai import OpenAI
from pydantic import BaseModel, Field, ConfigDict
from langchain_core.documents import Document, BaseDocumentCompressor

# 2. Re-usable Reranking Compressor (OpenAI SDK / LM Studio Hook)
class RerankResponse(BaseModel):
    score: float = Field(description="The relevance score from 0.0 to 1.0.")

class LMStudioQwenReranker(BaseDocumentCompressor):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    client: OpenAI = None
    top_n: int = None

    def __init__(self, client, top_n):
        super().__init__()
        self.client = client
        self.top_n = top_n

    def compress_documents(
        self, documents: Sequence[Document], query: str, callbacks = None
    ) -> Sequence[Document]:
        
        if not documents:
            return []

        scored_docs = []
        
        # Qwen3-Reranker requires a specific prompt layout to enforce score outputs
        system_instruction = (
            "You are an accurate reranking assistant. Given a query and a document context, "
            "calculate a relevance score between 0.0 and 1.0. "
        )

        for doc in documents:
            try:
                response = self.client.chat.completions.parse(
                    model="qwen3-reranker-0.6b",
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": f"Query: {query}\n\nDocument: {doc.page_content}"}
                    ],
                    temperature=0.0,
                    response_format=RerankResponse  # For Pydantic
                )
                score = response.choices[0].message.parsed.score if response.choices[0].message.parsed else 0.0
                doc.metadata["rerank_score"] = score
                scored_docs.append((doc, score))
            except Exception as e:
                print(f"A reranking error occured: {e}")
                scored_docs.append((doc, 0.0))

        scored_docs.sort(key=lambda x: x[1], reverse=True)
        print("RERANKING COMPLETE: ", scored_docs)          #NOTE: Remove later
        return [doc for doc, score in scored_docs[:self.top_n]]
