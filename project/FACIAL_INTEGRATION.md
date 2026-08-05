# 얼굴 특징(FacialFeature) 통합 가이드

이 문서는 `FacialFeatureExtractor`(MediaPipe FaceLandmarker 기반) 코드를 `monitor_main.py`에 통합하는 방법을 설명합니다.

## 요약
- **목적**: 영상에서 EAR, 눈썹-눈 거리, 입 주변 떨림(lip_tremor), 동공 흔들림(pupil_jitter) 등을 계산해 모니터링 결과에 반영합니다.
- **권장 순서**: (C) 설정 추가 및 가이드 작성 ✅ → (A) 빠른 통합(기본, 동기 방식) ✅ → (B) 권장 통합(비동기(QThread)로 처리)

## 사전 준비

1. **모델 파일 내려받기** (인터넷이 연결된 환경에서 1회 실행):

```bash
mkdir -p model
wget -O model/face_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
```

(라즈베리파이/윈도우 환경에서는 `wget` 대신 `curl -L -o` 또는 브라우저 다운로드 사용)

2. **의존성 설치**:
```bash
pip install -r requirements.txt
# 또는 개별 설치:
pip install mediapipe>=0.10
```

## 설정 (`monitor_config.json`)

아래 항목을 `monitor_config.json`에 추가했습니다:

```json
{
  "face_integration": {
    "enabled": false,
    "face_model_path": "model/face_landmarker.task",
    "window_seconds": 30,
    "fs_video": 30.0,
    "publish_algorithm_mqtt": false,
    "algorithm_mqtt_topic": "sensor/algorithm_features",
    "algorithm_mqtt_qos": 1
  }
}
```

| 항목 | 기본값 | 설명 |
|------|-------|------|
| `enabled` | `false` | 얼굴 특징 추출 활성화 여부 |
| `face_model_path` | `model/face_landmarker.task` | FaceLandmarker 모델 파일 경로 |
| `window_seconds` | `30` | 윈도우 길이(초) — 한 번에 분석할 프레임 수 |
| `fs_video` | `30.0` | 비디오 샘플링 주파수(Hz) |
| `publish_algorithm_mqtt` | `false` | 요약 결과를 MQTT로 발행할지 여부 |
| `algorithm_mqtt_topic` | `sensor/algorithm_features` | 발행할 토픽 |
| `algorithm_mqtt_qos` | `1` | MQTT QoS 레벨 |

## 파일 구조

### 새로 추가된 파일

- **`processing/__init__.py`**: 패키지 모듈
- **`processing/micro_movement_features.py`**: 고주파 진동 감지(Jitter) 계산 유틸
  - `highpass_jitter_score()`: 시계열 데이터의 고주파 진동 크기 (입 떨림, 동공 흔들림 감지)
  - Scipy 이용 가능 시 Butterworth 필터 사용, 아니면 numpy 차분 기반 근사

- **`processing/facial_features.py`**: 얼굴 특징 추출 핵심
  - `FacialFeatureExtractor`: MediaPipe FaceLandmarker를 래핑
    - `process_frame(frame_bgr)`: 한 프레임에서 특징 추출 (EAR, 눈썹 거리, 입 위치, 시선 위치)
    - `process_window(frames, fs_video)`: 프레임 윈도우를 요약 (깜박임, 떨림 등)

- **`tests/test_micro_movement_features.py`**: Jitter 계산 단위테스트 (✅ 통과)
- **`tests/test_facial_features_logic.py`**: 얼굴 특징 로직 테스트 (✅ 통과)

### 수정된 파일

- **`monitor_main.py`**: 통합 로직 추가
  - 임포트: `FacialFeatureExtractor`, `deque`, `numpy`
  - `init_facial_features()`: 설정에서 활성화된 경우 추출기 초기화
  - `update_frame()`: 카메라 프레임을 버퍼에 적재
  - `_process_facial_window()`: 윈도우가 가득 찼을 때 요약 계산 및 DB/UI 업데이트
  - `closeEvent()`: 종료 시 리소스 정리

- **`monitor_config.json`**: 얼굴 통합 설정 섹션 추가

## 통합 포인트 요약

1. **활성화**: `monitor_config.json`에서 `face_integration.enabled`를 `true`로 설정
2. **초기화**: `StressMonitorApp.__init__`에서 `init_facial_features()` 호출
3. **프레임 수집**: `update_frame()` 루프에서 카메라 프레임을 `self.frame_buffer`에 보관
4. **윈도우 집계**: `window_frame_count`개 프레임이 쌓이면 `_process_facial_window()` 실행
5. **결과 반영**: 요약 결과를 `self.algorithm_fields`와 `self.server_state`에 저장
6. **리소스 정리**: 앱 종료 시 `self.ff_extractor.close()` 호출

## 특징 설명

### EAR (Eye Aspect Ratio) & 깜박임
- 눈 랜드마크에서 수직/수평 거리 비율로 계산
- 특정 임계값(기본 0.21) 이하로 떨어졌다가 올라오는 순간 = 깜박임
- `blink_rate_per_min`: 분당 깜박임 횟수

### 눈썹-눈 거리 (Brow Tension)
- 미간 찌푸림 정도의 근사 지표
- `brow_tension`: 양쪽 눈썹 내측과 눈 위 지점 간 픽셀 거리 평균

### 입 떨림 (Lip Tremor)
- 입술 주변 4점(모서리, 위/아래 중심)의 Y 좌표 변화를 추적
- 고주파 진동 크기를 RMS(Root Mean Square)로 계산
- `lip_tremor`: 값이 클수록 떨림 심함

### 동공 흔들림 (Pupil Jitter)
- 눈동자(iris) 위치를 눈 구석 대비 상대 위치로 계산
- 머리 움직임에 강건하게 설계 (구석 랜드마크 대비 상대위치 사용)
- X, Y 방향의 고주파 진동 크기 평균
- `pupil_jitter`: 값이 클수록 시선 불안정

## 성능 및 안전성

### 단계 (A) - 현재 구현
- **특징**: 동기(synchronous) 처리, 간단한 통합
- **장점**: 코드 단순, 빠른 프로토타이핑
- **단점**: UI가 brief하게 블로킹될 수 있음 (윈도우 처리 시)
- **권장**: 프로토타입, 테스트 환경

### 단계 (B) - 권장 (향후)
- **특징**: 비동기(QThread) 처리
- **장점**: UI 블로킹 없음, 확장 가능
- **단점**: 스레드 안전성(thread-safe) 구현 필요
- **구현**: `_process_facial_window()`를 QThread에서 실행

## 문제 해결

### 모델 파일 없음
```
RuntimeError: FaceLandmarker 모델을 열 수 없습니다 (model/face_landmarker.task).
먼저 모델 파일을 받아주세요...
```
**해결**: 위 "사전 준비" 섹션의 `wget` 명령 실행

### 얼굴 미감지
- 카메라 조도/각도 확인
- `face_detection_rate` (DB의 `face_detection_rate` 값) 확인

### 높은 CPU 사용
- `window_seconds` 값 감소 (예: 30초 → 15초)
- 카메라 프레임 레이트 감소 (예: 30fps → 15fps)

## 테스트 실행

```bash
# micro_movement_features 테스트
python -m pytest tests/test_micro_movement_features.py -v

# 얼굴 특징 로직 테스트 (모델 파일 불필요)
python -m pytest tests/test_facial_features_logic.py -v
```

## 다음 단계

### 단계 (B) 비동기 통합 (권장)
기본 통합(A)이 정상 동작하면, `_process_facial_window()`를 QThread로 변경해 UI 블로킹을 제거합니다.

### MQTT 발행
`publish_algorithm_mqtt`를 `true`로 설정하면 요약 결과를 지정된 토픽으로 발행할 수 있습니다.

### 데이터베이스 저장
현재 얼굴 특징들은 `self.algorithm_fields`와 `self.server_state`에만 저장됩니다.
필요시 DB 테이블에 새 컬럼 추가 후 저장 가능합니다.

---
**작성자**: 통합 가이드 자동 생성  
**최종 업데이트**: 2026-08-05  
**상태**: 단계 (C) ✅, 단계 (A) ✅ 완료 | 단계 (B) 대기 중
