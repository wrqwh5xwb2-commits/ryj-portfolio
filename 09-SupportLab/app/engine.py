"""可解释基线：字符 TF-IDF + 逻辑回归分诊；BM25 / TF-IDF 双路检索。

TF-IDF 是稀疏词项特征，不是 BERT 语义向量；此版本不调用生成式模型。
"""
import math
import re
from collections import Counter
from time import perf_counter

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from .dataset import TRAIN


def tokens(text):
    # 中文双字切片保留词序信息，英文按单词处理，无需下载分词模型。
    words = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", text.lower())
    return [t for w in words for t in ([w[i:i + 2] for i in range(len(w) - 1)] if re.fullmatch(r"[\u4e00-\u9fff]+", w) and len(w) > 1 else [w])]


class Triage:
    def __init__(self):
        texts, labels = zip(*[(text, label) for label, rows in TRAIN.items() for text in rows])
        self.vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(1, 3), sublinear_tf=True)
        self.model = LogisticRegression(C=8, max_iter=1000, random_state=42)
        self.model.fit(self.vectorizer.fit_transform(texts), labels)

    def predict(self, text):
        probabilities = self.model.predict_proba(self.vectorizer.transform([text]))[0]
        ranked = np.argsort(probabilities)[::-1]
        score = float(probabilities[ranked[0]])
        return {"category": str(self.model.classes_[ranked[0]]), "score": round(score, 3),
                "needs_review": score < .45,
                "alternatives": [{"category": str(self.model.classes_[i]), "score": round(float(probabilities[i]), 3)} for i in ranked[:3]]}


class Retriever:
    def __init__(self, documents):
        self.documents = documents
        self.vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 3), sublinear_tf=True)
        if not documents:
            self.matrix = None
            return
        texts = [d["title"] + " " + d["content"] for d in documents]
        self.matrix = self.vectorizer.fit_transform(texts)
        self.counts = [Counter(tokens(t)) for t in texts]
        self.lengths = [sum(c.values()) for c in self.counts]
        self.avg_len = sum(self.lengths) / len(texts)
        self.df = Counter(t for c in self.counts for t in c)

    def search(self, query, mode="hybrid", limit=3):
        if self.matrix is None:
            return []
        cosine = (self.matrix @ self.vectorizer.transform([query]).T).toarray().ravel()
        bm25 = np.zeros(len(self.documents))
        for term in set(tokens(query)):
            idf = math.log(1 + (len(self.documents) - self.df[term] + .5) / (self.df[term] + .5))
            for i, counter in enumerate(self.counts):
                freq = counter[term]
                bm25[i] += idf * freq * 2.5 / (freq + 1.5 * (.25 + .75 * self.lengths[i] / self.avg_len))
        # RRF 只融合有实际命中的文档，避免无关文档因排名得到非零分数。
        fused = np.zeros(len(self.documents))
        for scores in (cosine, bm25):
            for rank, i in enumerate(np.argsort(-scores), start=1):
                if scores[i] > 0:
                    fused[i] += 1 / (60 + rank)
        scores = {"hybrid": fused, "tfidf": cosine, "bm25": bm25}[mode]
        indices = np.argsort(-scores)[:limit]
        return [{**self.documents[i], "score": round(float(scores[i]), 5), "similarity": round(float(cosine[i]), 4),
                 "bm25": round(float(bm25[i]), 3)} for i in indices if scores[i] > 0]


def analyze(text, triage, retriever, mode="hybrid"):
    started = perf_counter()
    prediction = triage.predict(text)
    sources = retriever.search(text, mode)
    # 经验阈值是可调基线；低分只返回候选资料，避免把相似度当作正确率。
    supported = bool(sources and sources[0]["similarity"] >= .18)
    if supported:
        answer = "找到以下相关规范，请核对是否适用于当前订单：\n\n" + sources[0]["content"]
    else:
        answer = "当前知识库没有找到足够相关的处理依据。请补充订单状态或具体问题，或创建工单交由人工核实。"
    urgent = [word for word in ["被盗", "陌生", "重复扣款", "扣了两次", "扣了两遍", "冻结"] if word in text]
    return {"prediction": prediction, "sources": sources, "answer": answer, "supported": supported,
            "priority": "高" if urgent else "普通", "priority_reason": "命中风险词：" + "、".join(urgent) if urgent else "未命中预设风险词，仍可由人工调整",
            "mode": mode, "answer_mode": "原文摘录", "latency_ms": round((perf_counter() - started) * 1000, 1)}
