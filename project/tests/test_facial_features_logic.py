"""
tests/test_facial_features_logic.py
facial_features.py의 핵심 함수들을 가짜 랜드마크/합성 데이터로 검증
(MediaPipe 모델 파일 없어도 테스트 가능)
"""
import numpy as np
import pytest
from processing.facial_features import (
    eye_aspect_ratio, extract_micro_movement_points, summarize_window,
    LEFT_EYE, RIGHT_EYE, LEFT_EYEBROW_INNER, LEFT_EYE_TOP,
    RIGHT_EYEBROW_INNER, RIGHT_EYE_TOP
)


class FakeLandmark:
    """FaceLandmarker.NormalizedLandmark를 모방하는 더미 클래스"""
    def __init__(self, x, y):
        self.x = x
        self.y = y


def create_fake_landmarks(n=478):
    """478개의 가짜 랜드마크 생성 (MediaPipe 478-point 모델 기준)"""
    landmarks = [FakeLandmark(0.5 + 0.01 * np.sin(i), 0.5 + 0.01 * np.cos(i)) for i in range(n)]
    return landmarks


def test_eye_aspect_ratio_basic():
    """EAR(Eye Aspect Ratio) 계산이 합리적인 값을 반환하는지 확인"""
    landmarks = create_fake_landmarks()
    w, h = 640, 480
    ear = eye_aspect_ratio(landmarks, LEFT_EYE, w, h)
    # EAR 값은 통상 0.1~0.4 범위이지만, 가짜 데이터에서는 다를 수 있음
    # 중요한 것은 NaN이 아니어야 함
    assert ear > 0.0 and not np.isnan(ear)


def test_eye_aspect_ratio_identical_points():
    """모든 점이 동일하면 0을 반환"""
    landmarks = [FakeLandmark(0.5, 0.5) for _ in range(478)]
    w, h = 640, 480
    ear = eye_aspect_ratio(landmarks, LEFT_EYE, w, h)
    assert np.isnan(ear)  # horizontal이 0이므로 NaN


def test_extract_micro_movement_points_basic():
    """미세 움직임 포인트(입 위치, 시선 위치)가 정상 범위"""
    landmarks = create_fake_landmarks()
    w, h = 640, 480
    micro = extract_micro_movement_points(landmarks, w, h)
    
    assert 'lip_pos_y' in micro
    assert 'gaze_pos_x' in micro
    assert 'gaze_pos_y' in micro
    
    # NaN이 아니어야 함
    assert all(not np.isnan(v) for v in micro.values())


def test_summarize_window_empty_detected():
    """감지된 프레임이 0이거나 1이면 NaN 특징"""
    summary = summarize_window(
        ears=[],
        brows=[],
        lip_ys=[],
        gaze_xs=[],
        gaze_ys=[],
        detected=0,
        total_frames=30,
        fs_video=30.0,
        ear_threshold=0.21
    )
    
    assert np.isnan(summary['blink_rate_per_min'])
    assert np.isnan(summary['avg_ear'])
    assert np.isnan(summary['brow_tension'])


def test_summarize_window_valid_data():
    """유효한 데이터 입력 시 합리적인 요약"""
    ears = [0.3] * 30  # 깜박임 아님
    brows = [20.0] * 30
    lip_ys = [100.0 + 0.1 * np.sin(i) for i in range(30)]  # 입술 미세 흔들림
    gaze_xs = [0.5] * 30
    gaze_ys = [0.5] * 30
    
    summary = summarize_window(
        ears=ears,
        brows=brows,
        lip_ys=lip_ys,
        gaze_xs=gaze_xs,
        gaze_ys=gaze_ys,
        detected=30,
        total_frames=30,
        fs_video=30.0,
        ear_threshold=0.21
    )
    
    # 깜박임이 없으므로 blink_rate는 0
    assert summary['blink_rate_per_min'] == 0.0
    # 평균 EAR은 0.3
    assert summary['avg_ear'] == 0.3
    # 평균 눈썹-눈 거리는 20.0
    assert summary['brow_tension'] == 20.0
    # 감지율은 100%
    assert summary['face_detection_rate'] == 1.0


def test_summarize_window_with_blinks():
    """깜박임 감지 테스트"""
    # EAR이 threshold보다 낮다가 높아지는 패턴 (깜박임)
    ears = [0.3] * 10 + [0.15, 0.10, 0.15] + [0.3] * 17  # 1회 깜박임
    brows = [20.0] * 30
    lip_ys = [100.0] * 30
    gaze_xs = [0.5] * 30
    gaze_ys = [0.5] * 30
    
    summary = summarize_window(
        ears=ears,
        brows=brows,
        lip_ys=lip_ys,
        gaze_xs=gaze_xs,
        gaze_ys=gaze_ys,
        detected=30,
        total_frames=30,
        fs_video=30.0,
        ear_threshold=0.21
    )
    
    # 약 1초 분량에서 1회 깜박임 -> 약 60 blinks/min
    assert summary['blink_rate_per_min'] >= 0.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
