"""Recuperador léxico TF-IDF; no equivale a embeddings semánticos."""
import hashlib
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

STOPWORDS = "a al ante bajo con contra de del desde el ella en entre es esta este esto hay la las lo los o para por que se sin sobre su sus un una y como cual cuales cuando donde puedo debo hacer tengo quiero saber".split()

class Retriever:
    def __init__(self, path):
        raw = path.read_bytes()
        self.corpus_sha256 = hashlib.sha256(raw).hexdigest()
        documents = json.loads(raw)
        required = {"id", "title", "version", "roles", "text", "status", "approved_at", "synthetic"}
        if not documents or any(not required.issubset(d) for d in documents):
            raise ValueError("El corpus está vacío o carece de campos obligatorios.")
        if len({d['id'] for d in documents}) != len(documents):
            raise ValueError("Los identificadores documentales deben ser únicos.")
        self.documents = [d for d in documents if d['status'] == 'vigente']
        self.indexes = {}
        for role in ('operaciones', 'riesgos'):
            allowed = [d for d in self.documents if role in d['roles']]
            if not allowed:
                raise ValueError(f"No hay documentos vigentes para {role}.")
            vectorizer = TfidfVectorizer(strip_accents='unicode', lowercase=True,
                                         ngram_range=(1, 2), stop_words=STOPWORDS)
            matrix = vectorizer.fit_transform([d['title'] + ' ' + d['text'] for d in allowed])
            self.indexes[role] = (allowed, vectorizer, matrix)

    def catalog(self, role):
        return [{k: d[k] for k in ('id','title','version','approved_at')}
                for d in self.indexes[role][0]]

    def search(self, question, role, top_k, threshold):
        allowed, vectorizer, matrix = self.indexes[role]
        scores = cosine_similarity(vectorizer.transform([question]), matrix).ravel()
        ranked = sorted(range(len(scores)), key=lambda i: (-scores[i], allowed[i]['id']))
        return [{**allowed[i], 'score': round(float(scores[i]), 6)}
                for i in ranked[:top_k] if scores[i] >= threshold]
