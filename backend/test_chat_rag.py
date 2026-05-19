import sys
import logging
from analyzer.vector_db import vector_db
from analyzer.llm_client import call_llm

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def test_vector_db():
    print("\n" + "="*50)
    print("TESTING VECTOR DATABASE...")
    print("="*50)
    
    test_queries = [
        "What is the health score calculation?",
        "How is bus factor measured?",
        "What are code hotspots?",
        "hello there"
    ]
    
    for q in test_queries:
        print(f"\nQuery: '{q}'")
        matches = vector_db.query(q, top_k=2)
        for doc, score in matches:
            print(f"  -> Match: [{doc['title']}] (Similarity Score: {score:.4f})")

def test_llm_client():
    print("\n" + "="*50)
    print("TESTING LLM CLIENT & RAG RETRIEVAL...")
    print("="*50)
    
    # Test 1: Platform overview greeting
    query_1 = "Explain what Sentinel Prime does."
    matches = vector_db.query(query_1, top_k=2)
    context_blocks = [f"Source: {doc['title']}\nContent: {doc['content']}" for doc, score in matches if score > 0.05]
    
    system_prompt = "You are Sentinel Copilot. Explain dashboard concepts using the context.\n"
    if context_blocks:
        system_prompt += "\nCONTEXT:\n" + "\n---\n".join(context_blocks)
        
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query_1}
    ]
    
    print(f"\nSending message: '{query_1}'")
    try:
        reply, model_used = call_llm(messages, [doc for doc, score in matches if score > 0.05])
        print(f"Response (Model: {model_used}):")
        print("-" * 40)
        print(reply)
        print("-" * 40)
    except Exception as e:
        print(f"LLM Call failed: {e}")

if __name__ == "__main__":
    test_vector_db()
    test_llm_client()
