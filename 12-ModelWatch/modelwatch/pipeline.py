"""Train once, evaluate separate batches, and build genuine Evidently reports."""

import argparse
import hashlib
import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path

os.environ["DO_NOT_TRACK"] = "1"
os.environ["EVIDENTLY_DISABLE_TELEMETRY"] = "1"

import evidently
import numpy as np
import pandas as pd
import sklearn
from evidently import BinaryClassification, DataDefinition, Dataset, Report
from evidently.metrics import Accuracy, F1Score, LogLoss, Precision, Recall, RocAuc
from evidently.presets import DataDriftPreset
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, log_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .data import FEATURES, SEED, make_batches

ROOT = Path(__file__).resolve().parents[1]
PSI_THRESHOLD = 0.2
DRIFT_SHARE = 0.4
QUALITY_DROP = 0.05
SCENARIOS = {
    "stable": ("正常批次", "独立抽取的同分布样本，作为基线对照。"),
    "sensor_shift": ("传感器偏移", "温度 +2.0、振动 +1.5；原始状态标签不变。"),
    "concept_shift": ("标签关系反转", "输入和正常批次完全一致，但标签反转，用于演示概念漂移。"),
}


def train_model(train: pd.DataFrame):
    # 标准化器与分类器只在训练批上拟合，避免评价信息进入训练。
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=500, random_state=SEED))
    model.fit(train[FEATURES], train["target"])
    return model


def predict(model, frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy(deep=True)
    result["probability"] = model.predict_proba(frame[FEATURES])[:, 1]
    result["prediction"] = (result["probability"] >= 0.5).astype(int)
    return result


def quality(frame: pd.DataFrame) -> dict:
    return {
        "accuracy": float(accuracy_score(frame["target"], frame["prediction"])),
        "f1": float(f1_score(frame["target"], frame["prediction"], zero_division=0)),
        "roc_auc": float(roc_auc_score(frame["target"], frame["probability"])),
        "log_loss": float(log_loss(frame["target"], frame["probability"])),
    }


def dataset(frame: pd.DataFrame) -> Dataset:
    data = frame.copy()
    data["target"] = data["target"].astype(str)
    data["prediction"] = data["prediction"].astype(str)
    schema = DataDefinition(
        id_column="sample_id",
        numerical_columns=FEATURES + ["probability"],
        categorical_columns=["target", "prediction"],
        classification=[BinaryClassification(
            target="target", prediction_labels="prediction",
            prediction_probas="probability", pos_label="1",
        )],
    )
    return Dataset.from_pandas(data, data_definition=schema)


def build_report(current: pd.DataFrame, reference: pd.DataFrame):
    return Report([
        DataDriftPreset(
            columns=FEATURES, method="psi", threshold=PSI_THRESHOLD,
            drift_share=DRIFT_SHARE, include_tests=False,
        ),
        # 0.7.23 的 ClassificationPreset(include_tests=False) 在按类别指标上
        # 触发 list/items 错误；使用官方独立指标组合，避免改动第三方源码。
        Accuracy(), F1Score(), Precision(), Recall(), RocAuc(), LogLoss(),
    ], include_tests=False).run(dataset(current), dataset(reference))


def summarize_report(report_dict: dict) -> dict:
    """Extract values computed by Evidently, without reimplementing drift detection."""
    columns = {}
    drift_count = None
    accuracy = None
    for metric in report_dict["metrics"]:
        kind = metric["config"]["type"].split(":")[-1]
        if kind == "ValueDrift":
            name = metric["config"]["column"]
            value = float(metric["value"])
            columns[name] = {"psi": value, "drifted": value >= PSI_THRESHOLD}
        elif kind == "DriftedColumnsCount":
            drift_count = int(metric["value"]["count"])
        elif kind == "Accuracy":
            accuracy = float(metric["value"])
    if drift_count is None or accuracy is None or set(columns) != set(FEATURES):
        raise ValueError("Evidently 报告结构改变，未找到预期指标；请使用锁定依赖。")
    return {"drifted_count": drift_count, "columns": columns, "evidently_accuracy": accuracy}


def alerts(drift_count: int, current_accuracy: float, reference_accuracy: float) -> list[str]:
    result = []
    if drift_count / len(FEATURES) >= DRIFT_SHARE:
        result.append("输入漂移：检查采集管道与特征分布")
    if reference_accuracy - current_accuracy >= QUALITY_DROP:
        result.append("效果下降：准确率比参考批降低至少 5 个百分点")
    return result


def fingerprint(frame: pd.DataFrame) -> str:
    return hashlib.sha256(frame.to_csv(index=False).encode("utf-8")).hexdigest()


def run(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    batches = make_batches()
    model = train_model(batches["train"])
    reference = predict(model, batches["reference"])
    reference_quality = quality(reference)
    results = []
    for name, (title, description) in SCENARIOS.items():
        current = predict(model, batches[name])
        report = build_report(current, reference)
        raw = report.dict()
        report.save_html(str(output / f"{name}.html"))
        (output / f"{name}.json").write_text(report.json(), encoding="utf-8")
        measured = quality(current)
        monitored = summarize_report(raw)
        if not np.isclose(monitored["evidently_accuracy"], measured["accuracy"]):
            raise AssertionError("Evidently 与 sklearn 的准确率不一致。")
        results.append({
            "id": name, "title": title, "description": description,
            "rows": len(current), "quality": measured, **monitored,
            "alerts": alerts(monitored["drifted_count"], measured["accuracy"], reference_quality["accuracy"]),
            "data_sha256": fingerprint(batches[name]),
        })

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
        "versions": {"python": platform.python_version(), "evidently": evidently.__version__,
                     "sklearn": sklearn.__version__, "numpy": np.__version__, "pandas": pd.__version__},
        "data": {"source": "原创合成数据；没有真实设备或客户数据", "train_rows": len(batches["train"]),
                 "reference_rows": len(reference), "current_rows": len(batches["stable"]),
                 "train_sha256": fingerprint(batches["train"]),
                 "reference_sha256": fingerprint(batches["reference"])},
        "thresholds": {"psi": PSI_THRESHOLD, "drift_share": DRIFT_SHARE, "accuracy_drop": QUALITY_DROP},
        "reference_quality": reference_quality,
        "scenarios": results,
    }
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    from .presentation import render_index
    (output / "index.html").write_text(render_index(summary), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main():
    parser = argparse.ArgumentParser(description="运行 ModelWatch，生成本地 HTML 监测报告")
    parser.add_argument("--output", type=Path, default=ROOT / "reports")
    arguments = parser.parse_args()
    run(arguments.output.resolve())


if __name__ == "__main__":
    main()
