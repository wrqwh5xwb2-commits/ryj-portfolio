"""固定模拟评测集；不读取用户导入的数据，不向业务数据库插入测试记录。"""
from datetime import datetime, timezone
import hashlib
import json
from time import perf_counter

import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

from .dataset import DOCUMENTS, RETRIEVAL_TEST, TEST, TRAIN, UNKNOWN_TEST
from .engine import Retriever, Triage, analyze


def run_evaluation():
    triage = Triage()
    docs = [dict(id=i, title=t, category=c, content=x) for i, t, c, x in DOCUMENTS]
    retriever = Retriever(docs)
    truth, predictions, cases = [], [], []
    for category, texts in TEST.items():
        for text in texts:
            result = triage.predict(text)
            truth.append(category)
            predictions.append(result["category"])
            cases.append(dict(text=text, expected=category, predicted=result["category"], score=result["score"], correct=result["category"] == category))
    labels = sorted(TRAIN)
    comparisons = []
    for mode in ("tfidf", "bm25", "hybrid"):
        hits, reciprocal, latencies, details = [], [], [], []
        for query, expected in RETRIEVAL_TEST:
            started = perf_counter()
            found = retriever.search(query, mode)
            latencies.append((perf_counter() - started) * 1000)
            ids = [d["id"] for d in found]
            rank = ids.index(expected) + 1 if expected in ids else None
            hits.append(rank is not None)
            reciprocal.append(1 / rank if rank else 0)
            details.append(dict(query=query, expected=expected, retrieved=ids, rank=rank))
        comparisons.append(dict(mode=mode, recall_at_3=round(float(np.mean(hits)), 4), mrr_at_3=round(float(np.mean(reciprocal)), 4),
                                p95_ms=round(float(np.percentile(latencies, 95)), 2), cases=details))
    unknown_cases = [dict(query=q, abstained=not analyze(q, triage, retriever)["supported"]) for q in UNKNOWN_TEST]
    known_cases = [dict(query=q, supported=analyze(q, triage, retriever)["supported"]) for q, _ in RETRIEVAL_TEST]
    corpus = json.dumps([TRAIN, TEST, DOCUMENTS, RETRIEVAL_TEST, UNKNOWN_TEST], ensure_ascii=False, sort_keys=True)
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "dataset_sha256": hashlib.sha256(corpus.encode()).hexdigest(),
            "scope": "原创模拟数据；固定开发评测集，非盲测。小样本结果不能代表真实客服效果。时延只测本机检索，不含网络。",
            "counts": {"train": sum(map(len, TRAIN.values())), "classification_test": len(truth), "retrieval_test": len(RETRIEVAL_TEST), "unknown_test": len(UNKNOWN_TEST), "documents": len(docs)},
            "classification": {"accuracy": round(accuracy_score(truth, predictions), 4), "macro_f1": round(f1_score(truth, predictions, average="macro"), 4), "labels": labels,
                               "confusion_matrix": confusion_matrix(truth, predictions, labels=labels).tolist(), "cases": cases},
            "retrieval": comparisons, "unknown_abstention_rate": round(float(np.mean([x["abstained"] for x in unknown_cases])), 4),
            "known_coverage": round(float(np.mean([x["supported"] for x in known_cases])), 4), "unknown_cases": unknown_cases, "known_cases": known_cases}


if __name__ == "__main__":
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / "data" / "evaluation.json"
    path.parent.mkdir(exist_ok=True)
    report = run_evaluation()
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(path), "classification": {k: report["classification"][k] for k in ("accuracy", "macro_f1")}, "retrieval": [{k: v for k, v in r.items() if k != "cases"} for r in report["retrieval"]], "known_coverage": report["known_coverage"], "unknown_abstention_rate": report["unknown_abstention_rate"]}, ensure_ascii=False, indent=2))
