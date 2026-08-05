"""
얼굴 특징 추출 (MediaPipe Tasks API - FaceLandmarker, mediapipe>=0.10 기준)
------------------------------------
- 눈 깜박임 비율(EAR)로 깜박임 빈도 추정
- 눈썹-눈 간 거리로 미간 찌푸림 정도 근사
- [신규] 입 떨림(lip_tremor): 입술 주변 랜드마크의 고주파 진동 크기
- [신규] 동공/시선 흔들림(pupil_jitter): 눈동자(iris)가 눈 안에서 흔들리는 정도
  (머리를 움직여도 눈 구석 랜드마크 대비 '상대 위치'로 계산하므로 머리 움직임의
  영향을 최대한 배제합니다)

떨림/흔들림 계산 원리는 micro_movement_features.py의 하이패스 필터를 사용합니다.

사전 준비 (인터넷 연결된 환경, 예: 라즈베리파이에서 1회 실행):
    wget -O model/face_landmarker.task \
      https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
※ 이 샌드박스에는 네트워크가 없어 모델 파일을 받을 수 없으므로, 얼굴 인식
자체는 여기서 끝까지 테스트하지 못했습니다. 아래 계산 로직들은
tests/test_facial_features_logic.py, tests/test_micro_movement_features.py에서
가짜 랜드마크/합성 신호로 별도 검증했습니다.
"""
from __future__ import annotations
from typing import Optional, Dict, List
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import vision as mp_vision
from mediapipe.tasks.python import BaseOptions

from processing.micro_movement_features import highpass_jitter_score

DEFAULT_MODEL_PATH = "model/face_landmarker.task"

# MediaPipe FaceMesh 468(+iris 10)점 표준 인덱스
LEFT_EYE = [33, 160, 158, 133, 153, 144]      # [바깥, 위1, 위2, 안쪽, 아래1, 아래2]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]
LEFT_EYEBROW_INNER, LEFT_EYE_TOP = 55, 159
RIGHT_EYEBROW_INNER, RIGHT_EYE_TOP = 285, 386

# 입 주변 (떨림 감지용)
MOUTH_LEFT_CORNER = 61
MOUTH_RIGHT_CORNER = 291
UPPER_LIP_CENTER = 13
LOWER_LIP_CENTER = 14

# 눈동자(iris) - refine_landmarks 사용 시 478점 모델에서 제공되는 홍채 랜드마크
LEFT_IRIS = [474, 475, 476, 477]
RIGHT_IRIS = [469, 470, 471, 472]


def eye_aspect_ratio(landmarks, indices, w, h) -> float:
    """랜드마크 리스트(.x/.y 속성을 가진 객체)에서 EAR 계산. 단위테스트에서도 재사용."""
    pts = np.array([(landmarks[i].x * w, landmarks[i].y * h) for i in indices])
    vertical1 = np.linalg.norm(pts[1] - pts[5])
    vertical2 = np.linalg.norm(pts[2] - pts[4])
    horizontal = np.linalg.norm(pts[0] - pts[3])
    if horizontal == 0:
        return float("nan")
    return (vertical1 + vertical2) / (2.0 * horizontal)


def extract_micro_movement_points(landmarks, w, h) -> Dict:
    """
    한 프레임에서 '입 위치'와 '눈 안에서의 동공 위치'를 얼굴 크기로 정규화해 추출.
    - 정규화 기준(inter_ocular_dist)으로 나누는 이유: 카메라와의 거리, 얼굴 크기
      차이에 상관없이 같은 스케일로 비교하기 위함.
    - gaze는 '눈 구석 대비 상대 위치'로 계산하므로, 머리를 좌우로 살짝 움직여도
      실제 눈동자가 눈 안에서 안 움직였다면 값이 크게 변하지 않음.
    단위테스트에서도 재사용하기 위해 순수 함수로 분리.
    """
    def pt(i):
        return np.array([landmarks[i].x * w, landmarks[i].y * h])

    left_eye_outer, left_eye_inner = pt(LEFT_EYE[0]), pt(LEFT_EYE[3])
    right_eye_outer, right_eye_inner = pt(RIGHT_EYE[0]), pt(RIGHT_EYE[3])
    inter_ocular_dist = np.linalg.norm(left_eye_outer - right_eye_outer)

    if inter_ocular_dist == 0:
        return {"lip_pos_y": np.nan, "gaze_pos_x": np.nan, "gaze_pos_y": np.nan}

    # 입 중심 위치 (얼굴 크기로 정규화)
    lip_center = (pt(UPPER_LIP_CENTER) + pt(LOWER_LIP_CENTER) +
                  pt(MOUTH_LEFT_CORNER) + pt(MOUTH_RIGHT_CORNER)) / 4.0
    lip_pos_y = lip_center[1] / inter_ocular_dist

    # 동공(홍채) 중심이 눈 구석 대비 어디에 있는지 (0~1에 가까운 상대 위치)
    left_iris_center = np.mean([pt(i) for i in LEFT_IRIS], axis=0)
    right_iris_center = np.mean([pt(i) for i in RIGHT_IRIS], axis=0)

    left_eye_width = np.linalg.norm(left_eye_inner - left_eye_outer)
    right_eye_width = np.linalg.norm(right_eye_inner - right_eye_outer)
    left_gaze_x = (np.linalg.norm(left_iris_center - left_eye_outer) / left_eye_width
                   if left_eye_width > 0 else np.nan)
    right_gaze_x = (np.linalg.norm(right_iris_center - right_eye_outer) / right_eye_width
                    if right_eye_width > 0 else np.nan)
    gaze_pos_x = np.nanmean([left_gaze_x, right_gaze_x])

    left_gaze_y = left_iris_center[1] / inter_ocular_dist
    right_gaze_y = right_iris_center[1] / inter_ocular_dist
    gaze_pos_y = np.nanmean([left_gaze_y, right_gaze_y])

    return {
        "lip_pos_y": float(lip_pos_y),
        "gaze_pos_x": float(gaze_pos_x),
        "gaze_pos_y": float(gaze_pos_y),
    }


def summarize_window(ears: list, brows: list, lip_ys: list, gaze_xs: list, gaze_ys: list,
                      detected: int, total_frames: int, fs_video: float, ear_threshold: float) -> Dict:
    """프레임별 특징 리스트 -> 윈도우 요약 특징. 단위테스트에서도 재사용."""
    face_detection_rate = detected / total_frames if total_frames else 0.0
    if detected < 2:
        return {
            "blink_rate_per_min": float("nan"),
            "avg_ear": float("nan"),
            "brow_tension": float("nan"),
            "lip_tremor": float("nan"),
            "pupil_jitter": float("nan"),
            "face_detection_rate": round(face_detection_rate, 2),
        }

    ears_arr = np.array(ears)
    below = ears_arr < ear_threshold
    blinks = np.sum(below[1:] & ~below[:-1])
    duration_min = (total_frames / fs_video) / 60.0
    blink_rate = blinks / duration_min if duration_min > 0 else float("nan")

    lip_tremor = highpass_jitter_score(np.array(lip_ys), fs=fs_video)
    jitter_x = highpass_jitter_score(np.array(gaze_xs), fs=fs_video)
    jitter_y = highpass_jitter_score(np.array(gaze_ys), fs=fs_video)
    pupil_jitter = float(np.nanmean([jitter_x, jitter_y]))

    return {
        "blink_rate_per_min": round(float(blink_rate), 1),
        "avg_ear": round(float(np.mean(ears_arr)), 3),
        "brow_tension": round(float(np.mean(brows)), 2),
        "lip_tremor": round(lip_tremor, 5) if not np.isnan(lip_tremor) else float("nan"),
        "pupil_jitter": round(pupil_jitter, 5) if not np.isnan(pupil_jitter) else float("nan"),
        "face_detection_rate": round(face_detection_rate, 2),
    }


class FacialFeatureExtractor:
    def __init__(self, model_path: str = DEFAULT_MODEL_PATH, ear_blink_threshold: float = 0.21):
        try:
            options = mp_vision.FaceLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=model_path),
                running_mode=mp_vision.RunningMode.IMAGE,
                num_faces=1,
                output_face_blendshapes=False,
            )
            self.landmarker = mp_vision.FaceLandmarker.create_from_options(options)
        except Exception as e:
            raise RuntimeError(
                f"FaceLandmarker 모델을 열 수 없습니다 ({model_path}). "
                "먼저 모델 파일을 받아주세요:\n"
                "  wget -O model/face_landmarker.task "
                "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
                "face_landmarker/float16/1/face_landmarker.task"
            ) from e
        self.ear_threshold = ear_blink_threshold

    def process_frame(self, frame_bgr: np.ndarray) -> Optional[Dict]:
        if frame_bgr is None or frame_bgr.size == 0:
            return None
        h, w = frame_bgr.shape[:2]

        try:
            rgb = np.ascontiguousarray(frame_bgr[:, :, ::-1])
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = self.landmarker.detect(mp_image)
        except Exception:
            # 프레임 하나가 손상되어도 윈도우 전체(30초 분량)가 죽지 않도록
            # 이 프레임만 '미검출'로 처리하고 계속 진행
            return None

        if not result.face_landmarks:
            return None

        lm = result.face_landmarks[0]
        required_max_index = max(
            LEFT_EYE + RIGHT_EYE + LEFT_IRIS + RIGHT_IRIS +
            [LEFT_EYEBROW_INNER, LEFT_EYE_TOP, RIGHT_EYEBROW_INNER, RIGHT_EYE_TOP,
             MOUTH_LEFT_CORNER, MOUTH_RIGHT_CORNER, UPPER_LIP_CENTER, LOWER_LIP_CENTER]
        )
        if len(lm) <= required_max_index:
            # 모델 설정이 예상과 달라 iris 랜드마크가 없는 경우 등 (478점이 아닌 468점)
            return None

        left_ear = eye_aspect_ratio(lm, LEFT_EYE, w, h)
        right_ear = eye_aspect_ratio(lm, RIGHT_EYE, w, h)
        avg_ear = np.nanmean([left_ear, right_ear])

        brow_dist_l = abs(lm[LEFT_EYEBROW_INNER].y - lm[LEFT_EYE_TOP].y) * h
        brow_dist_r = abs(lm[RIGHT_EYEBROW_INNER].y - lm[RIGHT_EYE_TOP].y) * h
        brow_dist = (brow_dist_l + brow_dist_r) / 2.0

        micro = extract_micro_movement_points(lm, w, h)

        return {"ear": float(avg_ear), "brow_distance": float(brow_dist), **micro}

    def detect_landmarks_for_viz(self, frame_bgr: np.ndarray) -> Optional[tuple]:
        """
        프레임에서 얼굴 특징점을 감지해 visualization용으로 반환합니다.
        Returns: (landmarks, face_bbox) 또는 None
          - landmarks: MediaPipe face_landmarks[0] (478점)
          - face_bbox: (x1, y1, x2, y2) 정규화된 좌표
        """
        if frame_bgr is None or frame_bgr.size == 0:
            return None
        h, w = frame_bgr.shape[:2]

        try:
            rgb = np.ascontiguousarray(frame_bgr[:, :, ::-1])
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = self.landmarker.detect(mp_image)
        except Exception as e:
            return None

        if not result.face_landmarks:
            return None

        lm = result.face_landmarks[0]
        
        # 간단한 bounding box: 모든 랜드마크의 최소/최대 좌표
        x_coords = [pt.x for pt in lm]
        y_coords = [pt.y for pt in lm]
        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)
        
        # 약간 여유 주기 (padding)
        pad_x = (x_max - x_min) * 0.1
        pad_y = (y_max - y_min) * 0.1
        face_bbox = (
            max(0, x_min - pad_x),
            max(0, y_min - pad_y),
            min(1, x_max + pad_x),
            min(1, y_max + pad_y)
        )
        
        return (lm, face_bbox)

    def process_window(self, frames: list, fs_video: float) -> Dict:
        """
        여러 프레임(윈도우, 예: 30초 분량)을 처리해 요약 특징을 계산합니다.
        - blink_rate_per_min, avg_ear, brow_tension
        - lip_tremor: 입 주변 랜드마크의 고주파 진동 크기 (클수록 입 떨림 큼)
        - pupil_jitter: 눈 안에서 동공이 흔들리는 정도 (클수록 시선이 불안정)
        """
        ears, brows, lip_ys, gaze_xs, gaze_ys = [], [], [], [], []
        detected = 0
        for frame in frames:
            feat = self.process_frame(frame)
            if feat is None:
                continue
            detected += 1
            ears.append(feat["ear"])
            brows.append(feat["brow_distance"])
            lip_ys.append(feat["lip_pos_y"])
            gaze_xs.append(feat["gaze_pos_x"])
            gaze_ys.append(feat["gaze_pos_y"])

        return summarize_window(ears, brows, lip_ys, gaze_xs, gaze_ys,
                                 detected, len(frames), fs_video, self.ear_threshold)

    def close(self):
        self.landmarker.close()
