"""Run Evidently's official README example, preserving its original split and API.

Source: evidentlyai/evidently@34771fe41c08ca074d96a52aaf4a45cd640cbaf5
README.md, "Data and ML evals", Apache-2.0 (see LICENSE-Evidently.txt).
Local changes: disable telemetry, add CLI entry point and persist evidence.
The ordered Iris split is an upstream demonstration, not a valid model evaluation.
"""

import json
import os
from pathlib import Path

os.environ["DO_NOT_TRACK"] = "1"
os.environ["EVIDENTLY_DISABLE_TELEMETRY"] = "1"

import pandas as pd  # Kept from the upstream example.
from sklearn import datasets

from evidently import Report
from evidently.presets import DataDriftPreset


def main():
    iris_data = datasets.load_iris(as_frame=True)
    iris_frame = iris_data.frame
    report = Report([DataDriftPreset(method="psi")], include_tests="True")
    my_eval = report.run(iris_frame.iloc[:60], iris_frame.iloc[60:])

    destination = Path(__file__).resolve().parents[1] / "reports" / "upstream"
    destination.mkdir(parents=True, exist_ok=True)
    my_eval.save_html(str(destination / "iris-drift.html"))
    (destination / "iris-drift.json").write_text(my_eval.json(), encoding="utf-8")
    summary = {
        "source_commit": "34771fe41c08ca074d96a52aaf4a45cd640cbaf5",
        "source_path": "README.md#data-and-ml-evals",
        "current_rows": len(iris_frame.iloc[:60]),
        "reference_rows": len(iris_frame.iloc[60:]),
        "columns": list(iris_frame.columns),
        "html_bytes": (destination / "iris-drift.html").stat().st_size,
        "report_metric_count": len(my_eval.dict()["metrics"]),
        "status": "completed",
    }
    (destination / "run-summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
