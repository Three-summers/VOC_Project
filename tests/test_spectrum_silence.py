"""R34：全零时域信号被频谱模型转换成满量程。

``updateFromTimeDomain([0] * 512)`` 时幅度全部被夹到 1e-10，再除以自身最大值，
得到全频 0 dB；归一化后是满量程 1.0。无信号应与"最大信号"明确区分。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from voc_app.gui.spectrum_model import SpectrumDataModel


def test_all_zero_time_domain_is_floor_not_full_scale() -> None:
    model = SpectrumDataModel(bin_count=128)

    model.updateFromTimeDomain([0.0] * 512)

    data = list(model.spectrumData)
    assert max(data) <= 0.01, f"无信号被当成满量程：max={max(data)}"


def test_almost_zero_time_domain_is_floor() -> None:
    model = SpectrumDataModel(bin_count=128)

    model.updateFromTimeDomain([1e-18] * 512)

    data = list(model.spectrumData)
    assert max(data) <= 0.01, f"近零信号被当成满量程：max={max(data)}"


def test_real_tone_still_normalizes_to_full_scale_peak() -> None:
    model = SpectrumDataModel(bin_count=128)
    samples = np.sin(2 * np.pi * np.arange(1024) / 64.0)

    model.updateFromTimeDomain(samples)

    data = list(model.spectrumData)
    assert abs(max(data) - 1.0) < 0.05, "有信号时峰值仍应归一化到 1.0"
    assert min(data) >= 0.0
