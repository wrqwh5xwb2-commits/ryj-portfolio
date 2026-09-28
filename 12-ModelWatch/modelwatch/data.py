"""原创合成数据：以固定随机种子演示监测机制，不代表真实设备数据。"""

import numpy as np
import pandas as pd

FEATURES = ["temperature", "vibration", "pressure", "workload", "ambient_noise"]
SEED = 20260928


def batch(size: int, seed: int, prefix: str) -> pd.DataFrame:
    """每次使用独立随机流；所有输入都是无单位的标准化数值。"""
    rng = np.random.default_rng(seed)
    features = rng.normal(size=(size, len(FEATURES)))
    score = features @ np.array([1.2, 1.8, -0.8, 0.6, 0.0])
    probability = 1.0 / (1.0 + np.exp(-score))
    frame = pd.DataFrame(features, columns=FEATURES)
    frame["target"] = (rng.random(size) < probability).astype(int)
    frame["sample_id"] = [f"{prefix}-{i:05d}" for i in range(size)]
    return frame


def make_batches(seed: int = SEED) -> dict[str, pd.DataFrame]:
    """训练/参考/当前三批互不重叠；两个异常场景用当前批做配对实验。"""
    train = batch(6000, seed, "train")
    reference = batch(2000, seed + 1, "reference")
    stable = batch(2000, seed + 2, "current")

    # 模拟采集管道错误：显示值偏移，真实设备状态和标签保持原值。
    sensor_shift = stable.copy(deep=True)
    sensor_shift["temperature"] += 2.0
    sensor_shift["vibration"] += 1.5

    # 对照实验：输入不变，标签关系反转。这种极端设定用于讲解概念漂移。
    concept_shift = stable.copy(deep=True)
    concept_shift["target"] = 1 - concept_shift["target"]
    return {
        "train": train,
        "reference": reference,
        "stable": stable,
        "sensor_shift": sensor_shift,
        "concept_shift": concept_shift,
    }
