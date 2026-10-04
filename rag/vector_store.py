from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer


class LocalVectorStore:
    def __init__(self):
        self.documents = []
        self.vectorizer = None
        self.document_vectors = None

    def reset(self):
        self.documents = []
        self.vectorizer = None
        self.document_vectors = None

    def add_texts(self, texts):
        documents = [text.strip() for text in texts if text and text.strip()]
        if not documents:
            return

        self.documents.extend(documents)
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            max_features=50000,
            sublinear_tf=True,
        )
        self.document_vectors = self.vectorizer.fit_transform(self.documents)

    def search(self, query, top_k=5):
        if not self.documents or self.vectorizer is None or self.document_vectors is None:
            return []

        query_vector = self.vectorizer.transform([query])
        sims = cosine_similarity(query_vector, self.document_vectors)[0]

        ranked = []
        for index, score in enumerate(sims):
            if score > 0:
                ranked.append({"text": self.documents[index], "score": float(score)})

        ranked.sort(key=lambda item: item["score"], reverse=True)
        return ranked[:top_k]
