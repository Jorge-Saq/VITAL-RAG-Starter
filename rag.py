"""Student exercise: implement retrieval over the fictional clinic policies."""
import re
from pathlib import Path
import pandas as pd
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DOCS = Path(__file__).parent / "knowledge_base"
# Drop boilerplate shared by every document; keep "bill" for billing questions.
STOP_WORDS = (ENGLISH_STOP_WORDS - {"bill"}) | {"fictional", "harbor", "clinic", "policy"}

def tokenize(text):
    """Lowercase, drop stop words, and strip common endings."""
    words = re.findall(r"\b\w\w+\b", text.lower())
    return [re.sub(r"(ations|ation|ing|ed|s)$", "", w) for w in words if w not in STOP_WORDS]

def load_documents(directory=DOCS):
    """Return list of (filename, text) for *.txt files."""
    # TODO 1: Load documents in deterministic filename order.
    rows = [(path.name, path.read_text()) for path in directory.glob("*.txt")]
    df = pd.DataFrame(rows, columns=["filename", "text"])
    df = df.sort_values("filename")
    return list(df.itertuples(index=False, name=None))

def retrieve(question: str, k: int = 2, documents=None):
    """Return top-k (filename, text, score) matches using TF-IDF."""
    # TODO 2: Vectorize documents and query, rank cosine similarities.
    # Exclude zero-score matches; break ties by filename.
    if documents is None:
        documents = load_documents()
    if not documents:
        return []
    names, texts = zip(*documents)
    vectorizer = TfidfVectorizer(tokenizer=tokenize, lowercase=False, token_pattern=None)
    doc_vectors = vectorizer.fit_transform(texts)
    query_vector = vectorizer.transform([question])
    scores = cosine_similarity(query_vector, doc_vectors)[0]
    hits = [(n, t, float(s)) for n, t, s in zip(names, texts, scores) if s > 0]
    hits.sort(key=lambda h: (-h[2], h[0]))
    return hits[:k]

def build_context(results):
    """Format hits with [Source: filename] headers."""
    # TODO 3: Build the prompt context.
    return "\n\n".join(f"[Source: {name}]\n{text.strip()}" for name, text, _ in results)
