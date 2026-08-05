## 얼굴 특징 추출 통합 완료 요약

### 작업 완료 내용

**단계 C) 설정 및 가이드 작성** ✅
- `monitor_config.json`에 `face_integration` 섹션 추가 (disabled by default)
- `FACIAL_INTEGRATION.md` 가이드 문서 작성 (설정, 사용법, 문제 해결)

**단계 A) 기본 통합 구현** ✅ 
- `processing/` 패키지 생성
  - `micro_movement_features.py`: 고주파 진동(Jitter) 계산
  - `facial_features.py`: FacialFeatureExtractor 클래스 (알고리즘팀 코드)
  
- `monitor_main.py` 수정
  - `init_facial_features()`: 설정 기반 추출기 초기화
  - `update_frame()`: 카메라 프레임 → 버퍼 적재
  - `_process_facial_window()`: 윈도우 도달 시 요약 계산 및 업데이트
  - `closeEvent()`: 리소스 정리
  
- 단위테스트 작성 및 검증 (✅ 5/5, ✅ 6/6 통과)
  - `tests/test_micro_movement_features.py`
  - `tests/test_facial_features_logic.py`

**단계 B) 비동기 통합** ⏳ (권장 추후 구현)
- QThread 기반 비동기 처리로 UI 블로킹 제거 예정

### 새로 추가/수정된 파일

```
project/
├── processing/
│   ├── __init__.py                          [신규]
│   ├── micro_movement_features.py           [신규]
│   └── facial_features.py                   [신규]
├── tests/
│   ├── test_micro_movement_features.py      [신규]
│   └── test_facial_features_logic.py        [신규]
├── monitor_main.py                          [수정]
├── monitor_config.json                      [수정]
├── requirements.txt                         [수정]
└── FACIAL_INTEGRATION.md                    [신규]
```

### 빠른 시작

1. **모델 파일 다운로드** (인터넷 환경)
```bash
mkdir -p model
wget -O model/face_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
```

2. **의존성 설치**
```bash
pip install -r requirements.txt
```

3. **설정 활성화**
`monitor_config.json`에서 `face_integration.enabled`를 `true`로 변경

4. **실행**
```bash
python monitor_main.py
```

5. **테스트** (모델 파일 불필요)
```bash
python -m pytest tests/test_micro_movement_features.py -v
python -m pytest tests/test_facial_features_logic.py -v
```

### 추출되는 특징

| 특징 | 설명 | 범위 |
|------|------|------|
| `blink_rate_per_min` | 분당 깜박임 횟수 | 0 ~ ∞ (bpm) |
| `avg_ear` | 평균 안검(Eye Aspect Ratio) | 0.0 ~ 1.0+ |
| `brow_tension` | 눈썹-눈 거리(미간 찌푸림 지표) | 0 ~ ∞ (픽셀) |
| `lip_tremor` | 입 주변 고주파 진동(떨림) | 0 ~ ∞ (RMS) |
| `pupil_jitter` | 동공 흔들림(시선 불안정) | 0 ~ ∞ (상대위치) |
| `face_detection_rate` | 얼굴 감지율 | 0.0 ~ 1.0 |

### 다음 단계 (권장)

1. **실제 모델로 동작 확인**: 모델 파일 다운로드 후 라이브 테스트
2. **비동기 처리 (단계 B)**: `_process_facial_window()` → QThread로 변경해 UI 블로킹 제거
3. **MQTT 발행**: `publish_algorithm_mqtt` 활성화 후 결과 발행
4. **DB 저장**: 얼굴 특징 컬럼 추가 및 저장 로직 구현
5. **대시보드 확장**: web dashboard에 얼굴 특징 시각화 추가

### 주의사항

- **단계 A** (현재): 동기 처리 → UI가 간단히 블록될 수 있음
- 프레임 처리 비용이 크므로 높은 FPS 환경에서는 `window_seconds` 감소 권장
- 모델 파일 로드 실패 시 얼굴 추출이 비활성화되고 나머지 기능은 정상 동작

---
**마지막 업데이트**: 2026-08-05
