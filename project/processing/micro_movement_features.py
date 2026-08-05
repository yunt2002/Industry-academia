import numpy as np

def highpass_jitter_score(y: np.ndarray, fs: float) -> float:
    """
    시계열 데이터 y의 고주파 진동 크기(Jitter score)를 계산합니다.
    - y: 1차원 데이터 배열 (결측치 NaN 포함 가능)
    - fs: 비디오 샘플링 주파수 (Hz)
    
    scipy가 설치되어 있다면 Butterworth 하이패스 필터를 적용하고,
    그렇지 않다면 numpy의 1차 차분(diff)을 활용하여 고주파 성분을 강건하게 근사합니다.
    """
    if len(y) < 4:
        return float("nan")
    
    # NaN 처리: 선형 보간
    nans = np.isnan(y)
    if np.all(nans):
        return float("nan")
    
    y_clean = np.array(y, dtype=float)
    if np.any(nans):
        # 복사본 생성 후 보간
        x = np.arange(len(y_clean))
        y_clean[nans] = np.interp(x[nans], x[~nans], y_clean[~nans])
        
    # 버터워스 필터 시도
    try:
        from scipy.signal import butter, filtfilt
        # 차단 주파수 (예: 2.0Hz)
        cutoff = 2.0
        nyq = 0.5 * fs
        if cutoff < nyq:
            b, a = butter(2, cutoff / nyq, btype='high')
            filtered = filtfilt(b, a, y_clean)
            # 고주파 성분의 RMS(Root Mean Square) 리턴
            return float(np.sqrt(np.mean(filtered ** 2)))
    except Exception:
        pass
        
    # Scipy가 없거나 예외 발생 시 numpy 1차 차분 기반 (차분값의 RMS)
    diff = np.diff(y_clean)
    return float(np.sqrt(np.mean(diff ** 2)))
