from chunking import *

eval_set = [
    {
        "question": "What have I written about creativity?",
        "relevant_chunk_ids": [],
        "type": "factual_recall"
    },
    {
        "question": "What have I written about scuba diving?",
        "relevant_chunk_ids": [],
        "type": "negative"
    }
]

def evaluate_retrieval(eval_set, retriever):
    positive_results = []
    negative_results = []

    for item in eval_set:
        print(f"Evaluating question: {item["question"]}")
        docs = retriever.invoke(item["question"])
        print(docs)
        retrieved_ids = [doc.id for doc in docs]

        if item["type"] == "negative":
            # threshold already filtered internally — empty list = correct abstention
            correctly_abstained = len(docs) == 0
            negative_results.append({
                "question": item["question"],
                "correctly_abstained": correctly_abstained
            })
            continue

        relevant_ids = set(item["relevant_chunk_ids"])
        hits = set(retrieved_ids) & relevant_ids
        precision = len(hits) / len(retrieved_ids) if retrieved_ids else 0
        recall = len(hits) / len(relevant_ids) if relevant_ids else 0

        positive_results.append({
            "question": item["question"],
            "precision": precision,
            "recall": recall,
            "hit": len(hits) > 0
        })

    metrics = {
        "avg_precision": sum(r["precision"] for r in positive_results) / len(positive_results) if positive_results else None,
        "avg_recall": sum(r["recall"] for r in positive_results) / len(positive_results) if positive_results else None,
        "hit_rate": sum(r["hit"] for r in positive_results) / len(positive_results) if positive_results else None,
        "abstention_accuracy": sum(r["correctly_abstained"] for r in negative_results) / len(negative_results) if negative_results else None,
    }
    return metrics

if __name__ == "__main__":
    vec = VectorInterface()
    print("Interface instantiated...")

    print(json.dumps(evaluate_retrieval(eval_set, vec.retriever), indent=4))