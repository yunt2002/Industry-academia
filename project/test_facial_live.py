"""
얼굴 통합 라이브 테스트
모델 파일을 사용해 FacialFeatureExtractor가 정상 초기화되는지 확인합니다.
"""
import json
import os
import sys

# Config 로드
config_path = os.path.join(os.path.dirname(__file__), 'monitor_config.json')
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

print("=" * 60)
print("🎯 얼굴 통합 라이브 테스트")
print("=" * 60)

print("\n1️⃣  설정 확인")
face_config = config.get('face_integration', {})
print(f"   enabled: {face_config.get('enabled')}")
print(f"   model_path: {face_config.get('face_model_path')}")
print(f"   window_seconds: {face_config.get('window_seconds')}")

if not face_config.get('enabled'):
    print("\n❌ 얼굴 통합이 비활성화되어 있습니다!")
    sys.exit(1)

model_path = face_config.get('face_model_path', 'model/face_landmarker.task')
if not os.path.exists(model_path):
    print(f"\n❌ 모델 파일을 찾을 수 없습니다: {model_path}")
    sys.exit(1)

print(f"\n2️⃣  모델 파일 확인")
model_size = os.path.getsize(model_path)
print(f"   ✅ 모델 파일 존재: {model_path}")
print(f"   ✅ 파일 크기: {model_size / (1024*1024):.2f}MB")

print("\n3️⃣  FacialFeatureExtractor 초기화 시도")
try:
    from processing.facial_features import FacialFeatureExtractor
    extractor = FacialFeatureExtractor(model_path=model_path)
    print(f"   ✅ FacialFeatureExtractor 생성 성공!")
    print(f"   ✅ Landmarker 모델 로드됨")
    extractor.close()
    print(f"   ✅ 리소스 정리 완료")
except Exception as e:
    print(f"   ❌ 초기화 실패: {type(e).__name__}: {str(e)[:100]}")
    sys.exit(1)

print("\n4️⃣  monitor_main.py init_facial_features() 시뮬레이션")
try:
    import cv2
    import numpy as np
    from collections import deque
    
    # init_facial_features 로직 재현
    ff_extractor = None
    frame_buffer = None
    fs_video = float(face_config.get('fs_video', 30.0))
    window_seconds = int(face_config.get('window_seconds', 30))
    window_frame_count = int(fs_video * window_seconds)
    
    ff_extractor = FacialFeatureExtractor(model_path=model_path)
    frame_buffer = deque(maxlen=window_frame_count)
    
    print(f"   ✅ 초기화 완료")
    print(f"   ✅ 프레임 버퍼 크기: {window_frame_count}개")
    print(f"   ✅ 비디오 샘플링: {fs_video}Hz")
    
    # 테스트 프레임 생성 (검은색)
    test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = ff_extractor.process_frame(test_frame)
    
    if result is None:
        print(f"   ℹ️  테스트 프레임에서 얼굴 미감지 (예상된 결과)")
    else:
        print(f"   ✅ process_frame 결과: {result}")
    
    ff_extractor.close()
    print(f"   ✅ 정리 완료")
    
except Exception as e:
    print(f"   ❌ 오류: {type(e).__name__}: {str(e)[:100]}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ 모든 테스트 통과!")
print("=" * 60)
print("\n📝 다음 단계:")
print("   monitor_main.py를 정상 실행하면 얼굴 특징이 자동으로")
print("   추출되고 30초마다 요약 결과가 표시됩니다.")
print("\n실행 명령:")
print("   python monitor_main.py")
