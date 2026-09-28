"""Key safeguards: leakage, known scenario semantics, and real library behavior."""

import numpy as np
import pandas as pd
import pytest

from modelwatch.data import FEATURES, make_batches
from modelwatch.pipeline import alerts, build_report, predict, quality, summarize_report, train_model


@pytest.fixture(scope="module")
def batches():
    return make_batches()


@pytest.fixture(scope="module")
def evaluated(batches):
    model = train_model(batches["train"])
    return model, {name: predict(model, frame) for name, frame in batches.items() if name != "train"}


def test_train_reference_current_are_disjoint(batches):
    partitions = [set(batches[name]["sample_id"]) for name in ("train", "reference", "stable")]
    assert not (partitions[0] & partitions[1] or partitions[0] & partitions[2] or partitions[1] & partitions[2])
    assert sum(map(len, partitions)) == 10000


def test_scaler_fits_training_data_only(batches, evaluated):
    model, _ = evaluated
    scaler = model.named_steps["standardscaler"]
    np.testing.assert_allclose(scaler.mean_, batches["train"][FEATURES].mean().to_numpy())
    assert scaler.n_samples_seen_ == 6000


def test_data_is_reproducible(batches):
    regenerated = make_batches()
    for name in batches:
        pd.testing.assert_frame_equal(batches[name], regenerated[name])


def test_sensor_corruption_preserves_ground_truth(batches):
    current, corrupted = batches["stable"], batches["sensor_shift"]
    np.testing.assert_allclose(corrupted[FEATURES] - current[FEATURES], np.tile([2, 1.5, 0, 0, 0], (2000, 1)))
    pd.testing.assert_series_equal(current["target"], corrupted["target"])


def test_concept_scenario_changes_only_labels(batches):
    current, changed = batches["stable"], batches["concept_shift"]
    pd.testing.assert_frame_equal(current[FEATURES], changed[FEATURES])
    assert (current["target"] + changed["target"] == 1).all()


@pytest.mark.parametrize("scenario, expected_drift, accuracy_range", [
    ("stable", 0, (0.78, 0.85)),
    ("sensor_shift", 2, (0.45, 0.56)),
    ("concept_shift", 0, (0.15, 0.22)),
])
def test_real_evidently_metrics_and_model_behavior(evaluated, scenario, expected_drift, accuracy_range):
    _, frames = evaluated
    result = summarize_report(build_report(frames[scenario], frames["reference"]).dict())
    measured = quality(frames[scenario])
    assert result["drifted_count"] == expected_drift
    assert result["evidently_accuracy"] == pytest.approx(measured["accuracy"])
    assert accuracy_range[0] <= measured["accuracy"] <= accuracy_range[1]


def test_quality_alert_does_not_require_input_drift():
    assert len(alerts(0, 0.18, 0.80)) == 1
    assert len(alerts(2, 0.50, 0.80)) == 2
    assert not alerts(0, 0.81, 0.80)
