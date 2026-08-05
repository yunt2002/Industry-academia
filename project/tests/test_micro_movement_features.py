"""
tests/test_micro_movement_features.py
micro_movement_features.py의 highpass_jitter_score 함수 단위테스트
"""
import numpy as np
import pytest
from processing.micro_movement_features import highpass_jitter_score


def test_highpass_jitter_score_constant_signal():
    """상수 신호의 경우 jitter score는 0에 가까워야 함"""
    y = np.array([1.0, 1.0, 1.0, 1.0, 1.0])
    score = highpass_jitter_score(y, fs=30.0)
    assert score < 0.01  # 거의 0에 가까움


def test_highpass_jitter_score_sine_wave():
    """정현파의 경우 jitter score는 0이 아님"""
    fs = 30.0
    t = np.arange(0, 1, 1/fs)
    # 주파수 5Hz 정현파
    y = np.sin(2 * np.pi * 5 * t)
    score = highpass_jitter_score(y, fs=fs)
    assert score > 0.0


def test_highpass_jitter_score_with_nans():
    """NaN이 포함된 데이터도 처리 가능해야 함"""
    y = np.array([1.0, np.nan, 1.0, 1.0, 1.0])
    score = highpass_jitter_score(y, fs=30.0)
    assert not np.isnan(score)  # 결과가 NaN이 아님


def test_highpass_jitter_score_short_sequence():
    """시퀀스가 너무 짧으면 NaN 리턴"""
    y = np.array([1.0, 2.0])
    score = highpass_jitter_score(y, fs=30.0)
    assert np.isnan(score)


def test_highpass_jitter_score_all_nans():
    """모든 값이 NaN이면 NaN 리턴"""
    y = np.array([np.nan, np.nan, np.nan])
    score = highpass_jitter_score(y, fs=30.0)
    assert np.isnan(score)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
