from sentence_transformers import SentenceTransformer


class EmbeddingManager:
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            cls._model = SentenceTransformer("all-MiniLM-L6-v2")
        return cls._model

    def encode(self, texts):
        model = self.get_model()
        return model.encode(texts, convert_to_numpy=True)
