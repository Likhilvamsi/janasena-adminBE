from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def rank_by_similarity(query: str, documents: list[str], top_k: int = 10):
    """
    Returns indices of top similar documents using TF-IDF + cosine similarity
    """
    if not documents:
        return []

    vectorizer = TfidfVectorizer(stop_words="english")

    tfidf_matrix = vectorizer.fit_transform([query] + documents)

    similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()

    ranked_indices = similarities.argsort()[::-1][:top_k]

    return ranked_indices