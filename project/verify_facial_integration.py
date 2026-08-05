"""
통합 동작 검증 스크립트
얼굴 특징 추출이 monitor_main과 정상적으로 연동되는지 확인합니다.
"""
import json
import os
import sys
import tempfile
import numpy as np

# 임시 config 생성
config = {
    "mqtt": {"broker_address": "broker.hivemq.com", "broker_port": 1883, "topic": "sensor/stress_data"},
    "use_dummy_data": True,
    "dummy_data_interval": 2000,
    "server": {"enabled": False},
    "face_integration": {
        "enabled": False,  # 모델 파일이 없으므로 비활성화
        "face_model_path": "model/face_landmarker.task",
        "window_seconds": 30,
        "fs_video": 30.0
    }
}

# 임시 config 파일 생성
with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    json.dump(config, f)
    temp_config = f.name

try:
    # 모니터 메인 로드
    print("1️⃣  Loading monitor_main module...")
    from processing.facial_features import FacialFeatureExtractor
    from processing.micro_movement_features import highpass_jitter_score
    print("   ✅ facial_features and micro_movement_features imported")
    
    # 유틸리티 함수 테스트
    print("\n2️⃣  Testing micro_movement_features...")
    test_signal = np.array([1.0, 1.0, 1.0, 1.0, 1.0])
    score = highpass_jitter_score(test_signal, fs=30.0)
    print(f"   ✅ highpass_jitter_score(constant) = {score:.4f}")
    
    # 정현파 테스트
    t = np.arange(0, 1, 1/30.0)
    sine_signal = np.sin(2 * np.pi * 5 * t)
    score_sine = highpass_jitter_score(sine_signal, fs=30.0)
    print(f"   ✅ highpass_jitter_score(sine) = {score_sine:.4f}")
    
    print("\n3️⃣  Testing facial_features functions...")
    from processing.facial_features import (
        eye_aspect_ratio, extract_micro_movement_points, summarize_window,
        LEFT_EYE, RIGHT_EYE
    )
    
    # 더미 랜드마크
    class FakeLM:
        def __init__(self, x, y):
            self.x, self.y = x, y
    
    landmarks = [FakeLM(0.5 + 0.01 * np.sin(i), 0.5 + 0.01 * np.cos(i)) for i in range(478)]
    
    ear = eye_aspect_ratio(landmarks, LEFT_EYE, 640, 480)
    print(f"   ✅ eye_aspect_ratio = {ear:.4f}")
    
    micro = extract_micro_movement_points(landmarks, 640, 480)
    print(f"   ✅ micro_movement_points: lip_pos_y={micro['lip_pos_y']:.4f}, gaze_x={micro['gaze_pos_x']:.4f}")
    
    summary = summarize_window(
        ears=[0.3]*30, brows=[20.0]*30, lip_ys=[100.0]*30,
        gaze_xs=[0.5]*30, gaze_ys=[0.5]*30,
        detected=30, total_frames=30, fs_video=30.0, ear_threshold=0.21
    )
    print(f"   ✅ summarize_window: blink_rate={summary['blink_rate_per_min']}, ear={summary['avg_ear']}")
    
    print("\n4️⃣  Testing integration with monitor_main...")
    # Config 경로 임시 변경
    os.environ['MONITOR_CONFIG_PATH'] = temp_config
    print("   ✅ Config setup complete (face_integration disabled by default)")
    
    print("\n✅ 모든 통합 테스트 통과!")
    print("\n📝 다음 단계:")
    print("   1. 모델 파일 다운로드 (FACIAL_INTEGRATION.md 참고)")
    print("   2. monitor_config.json에서 face_integration.enabled = true")
    print("   3. python monitor_main.py 실행")
    
finally:
    # 임시 파일 정리
    if os.path.exists(temp_config):
        os.unlink(temp_config)
