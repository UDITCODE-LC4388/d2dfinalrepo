import re
import math
import logging
import numpy as np

logger = logging.getLogger(__name__)

# Structured platform knowledge base corpus
KNOWLEDGE_CORPUS = [
    {
        "id": "overview",
        "title": "Platform Overview & Purpose",
        "content": (
            "Sentinel Prime (Repository Health Intelligence) is a unified engineering intelligence platform "
            "designed for production-level git commit mining, repository ingestion, hotspot analysis, "
            "developer-commit collaboration graph mapping, and architecture health evaluation. It provides "
            "engineering managers, tech leads, and software architects with real-time, objective insight into "
            "codebase structural risks, developer workflow patterns, and code architecture complexity. "
            "It is configured to run as a FastAPI backend with an interactive dashboard frontend."
        ),
        "tags": ["sentinel", "prime", "platform", "overview", "purpose", "architecture", "hackathon", "what is"]
    },
    {
        "id": "health_score",
        "title": "Codebase Health Score Calculation",
        "content": (
            "The Health Score (also known as the codebase health index) is a primary metric rated out of 100 "
            "representing the overall structural health of a repository. A score above 85 represents excellent "
            "structural health, 65 to 85 represents stable baseline health, and below 45 signifies warning-level "
            "architectural risk. The health score is dynamically computed by combining commit volume and size metrics, "
            "file complexity deltas (derived from static Radon cyclomatic complexity values), file churn "
            "(how frequently files are modified), and architectural dependency stability. Stable repositories "
            "maintain high health scores by minimizing high-complexity file churn and avoiding tightly-coupled code."
        ),
        "tags": ["health", "score", "index", "metric", "calculation", "radon", "complexity", "formula"]
    },
    {
        "id": "bus_factor",
        "title": "Bus Factor & Team Health",
        "content": (
            "Bus Factor represents team knowledge concentration and engineering operational stability. It measures "
            "the minimum number of developers who carry critical knowledge of the codebase, meaning if they were "
            "struck by a bus or suddenly left, the project would stall due to lack of expertise. A low bus factor "
            "(less than 3) is a high-risk bottleneck indicating that only 1 or 2 developers are doing all the critical "
            "work or own all the domain expertise. High bus factors represent healthy, evenly distributed collaboration, "
            "shared ownership, and balanced knowledge sharing across the development team."
        ),
        "tags": ["bus", "factor", "team", "health", "bottleneck", "developer", "collaboration", "risk", "knowledge"]
    },
    {
        "id": "code_health",
        "title": "Code Health, Complexity & Churn",
        "content": (
            "Code Health is computed using static analysis to track file complexity deltas and file churn across git history. "
            "Churn measures how frequently a file is modified across commits, while complexity represents the cognitive "
            "weight of the code (tracked using Radon's Cyclomatic Complexity score). When a file has high complexity "
            "and experiences high churn (frequent modifications), it represents a high-risk development area that degrades "
            "overall Code Health and increases the probability of regressions. Re-factoring these high-churn files "
            "is highly recommended to restore codebase health."
        ),
        "tags": ["code", "health", "complexity", "churn", "radon", "refactoring", "cyclomatic", "regression"]
    },
    {
        "id": "architecture_stability",
        "title": "Architecture Health & Stability",
        "content": (
            "Architecture Health and Stability evaluates modularity, dependency trees, and circular dependency risks in "
            "the codebase. Derived from relative import dependency graphs extracted from the repository HEAD, it tracks "
            "how tightly coupled the repository modules are. A stable architecture (high stability percentage) minimizes "
            "cyclic dependencies, circular imports, and spaghetti-like coupling. Stable systems have clearly structured "
            "directed dependency trees where changes to one module do not ripple unstably through the rest of the application."
        ),
        "tags": ["architecture", "stability", "dependency", "circular", "import", "coupling", "modular", "graph"]
    },
    {
        "id": "hotspots",
        "title": "Codebase Hotspots",
        "content": (
            "Hotspots are files in the repository that suffer from both high churn (frequent modifications) and high "
            "cyclomatic complexity. In the dashboard heatmap, hotspots are color-coded: red represents critical files "
            "requiring urgent refactoring, yellow represents moderate risk, and green is healthy. These files are the "
            "primary vectors of architectural debt and developer friction. Refactoring hotspots by splitting complex "
            "classes and modules into smaller, single-responsibility files stabilizes the release cycle, reduces "
            "bug introduction rates, and improves developer onboarding velocity."
        ),
        "tags": ["hotspots", "heatmap", "churn", "complexity", "refactoring", "debt", "risk", "red"]
    },
    {
        "id": "collaboration_graph",
        "title": "Developer Collaboration Graph",
        "content": (
            "The Collaboration Graph is an interactive network visualization mapping relationships between developers "
            "and the git commits or files they modify. It exposes knowledge silos, developer-to-module coupling, "
            "and high-collaboration clusters. By visualizing these paths, engineering managers can identify who owns "
            "which part of the system, detect isolated developers who represent a single point of failure for specific "
            "modules, and optimize team alignment. This graph visualizes developer networks in real-time."
        ),
        "tags": ["collaboration", "graph", "network", "developer", "silo", "coupling", "teams", "visualization"]
    },
    {
        "id": "ai_copilot",
        "title": "AI Summaries & Sentinel Copilot",
        "content": (
            "AI Summaries and the Sentinel Copilot provide real-time, context-aware engineering insights. Sentinel Copilot "
            "is a senior software architect AI assistant integrated directly into the dashboard. AI features leverage the "
            "Backend API connected to a secure Vector DB for website knowledge, utilizing a multi-provider LLM backend "
            "(DeepSeek V3 as the primary model and Groq Llama-3.3-70b as a high-speed fallback) to analyze git commits "
            "and answer developer architectural queries dynamically. The assistant uses retrieval-augmented generation (RAG)."
        ),
        "tags": ["ai", "summary", "copilot", "chat", "assistant", "deepseek", "groq", "llm", "rag", "vector"]
    }
]

def tokenize(text):
    """Tokenize text into lowercase alpha words, filtering common stop words."""
    words = re.findall(r'\b[a-z]{2,}\b', text.lower())
    stopwords = {
        "the", "and", "of", "to", "in", "is", "for", "that", "it", "on", "with", "as",
        "by", "an", "at", "are", "from", "be", "this", "which", "or", "have", "has", "who"
    }
    return [w for w in words if w not in stopwords]

class MiniVectorDB:
    """
    A lightweight, high-performance in-memory Vector DB using a TF-IDF vector space 
    and cosine similarity. 100% self-contained and powered by NumPy.
    """
    def __init__(self):
        self.documents = KNOWLEDGE_CORPUS
        self.vocab = {}
        self.idf = {}
        self.doc_vectors = []
        self.build_index()

    def build_index(self):
        """Construct the TF-IDF index for the corpus."""
        # 1. Tokenize all documents and include tags heavily to boost matches
        tokenized_docs = []
        for doc in self.documents:
            # Combine content, title, and tags (multiplying tags/title to boost weight)
            combined_text = (
                doc["content"] + " " + 
                (doc["title"] + " ") * 3 + 
                " ".join(doc["tags"] * 4)
            )
            tokenized_docs.append(tokenize(combined_text))

        # 2. Build vocabulary
        vocab_set = set()
        for tokens in tokenized_docs:
            vocab_set.update(tokens)
        
        self.vocab = {word: i for i, word in enumerate(sorted(vocab_set))}
        vocab_size = len(self.vocab)
        num_docs = len(self.documents)

        if vocab_size == 0:
            logger.warning("Empty vocabulary constructed for Vector DB.")
            return

        # 3. Calculate IDF for each term
        # Standard smoothing: idf = log((1 + N) / (1 + df)) + 1
        for word, index in self.vocab.items():
            df = sum(1 for tokens in tokenized_docs if word in tokens)
            self.idf[word] = math.log((1 + num_docs) / (1 + df)) + 1.0

        # 4. Create document vectors
        self.doc_vectors = []
        for tokens in tokenized_docs:
            vec = np.zeros(vocab_size)
            # Count term frequencies (TF)
            if tokens:
                counts = {}
                for t in tokens:
                    counts[t] = counts.get(t, 0) + 1
                
                # Build TF-IDF weights
                for t, count in counts.items():
                    if t in self.vocab:
                        tf = count / len(tokens)
                        vec[self.vocab[t]] = tf * self.idf[t]
            
            # Normalize vector to unit length
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            
            self.doc_vectors.append(vec)
        
        logger.info("Successfully built in-memory Vector DB index with %d documents, vocabulary size of %d.", num_docs, vocab_size)

    def query(self, query_text, top_k=2):
        """
        Query the Vector DB with query text. 
        Returns a list of tuples: (document, similarity_score) sorted descending by score.
        """
        if not self.vocab:
            return []

        # Tokenize query
        query_tokens = tokenize(query_text)
        if not query_tokens:
            # Fallback to returning top documents if query has no recognized words
            return [(doc, 0.0) for doc in self.documents[:top_k]]

        # Build query vector
        query_vec = np.zeros(len(self.vocab))
        counts = {}
        for t in query_tokens:
            counts[t] = counts.get(t, 0) + 1

        for t, count in counts.items():
            if t in self.vocab:
                tf = count / len(query_tokens)
                query_vec[self.vocab[t]] = tf * self.idf[t]

        # Normalize query vector
        query_norm = np.linalg.norm(query_vec)
        if query_norm > 0:
            query_vec = query_vec / query_norm
        else:
            return [(doc, 0.0) for doc in self.documents[:top_k]]

        # Compute cosine similarity with all doc vectors
        results = []
        for i, doc_vec in enumerate(self.doc_vectors):
            similarity = float(np.dot(doc_vec, query_vec))
            results.append((self.documents[i], similarity))

        # Sort descending by score
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

# Global single instance of Vector DB
vector_db = MiniVectorDB()
