# Raspberry Pi Integration Guide

## 메시지 스키마 (JSON)
일반 권장 스키마:

```json
{
  "device_id": "raspi-01",
  "timestamp": "2026-08-03T03:19:04Z",
  "heart_rate": 78.5,
  "spo2": 97.0,
  "stress_level": 30.0
}
```

- `device_id` (string): 장치 식별자(선택)
- `timestamp` (string, ISO8601 UTC 권장): 측정 시각
- `heart_rate` (number): BPM
- `spo2` (number): 산소포화도(%)
- `stress_level` (number): 0-100 스케일

## 권장 MQTT 설정
- 토픽: `sensor/stress_data`
- QoS: 1
- Retain: false
- 전송 간격: 센서 특성에 따라 1-60초(테스트는 5초 권장)

## 샘플 퍼블리셔 실행
1. 라즈베리 또는 개발 PC에서 가상환경 생성 및 의존성 설치

```bash
python3 -m venv .venv
source .venv/bin/activate    # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. 예제 퍼블리셔 실행(시뮬레이션 모드)

```bash
python mqtt_publisher_example.py --broker broker.hivemq.com --topic sensor/stress_data --interval 5 --simulate
```

3. 퍼블리셔를 실제 센서로 연결하려면 `--simulate` 블록을 교체하여 센서 라이브러리에서 값을 읽어 `payload`를 구성하세요.

## 테스트 절차 (서버 쪽)
1. 서버가 실행 중인지 확인: `http://<server>:8765/health` → `{"status":"ok"}`
2. 최근 저장 확인: `http://<server>:8765/api/history?limit=5`
3. 실시간 최신값 확인: `http://<server>:8765/latest`
4. 대시보드(브라우저): `http://<server>:8765/dashboard?lang=ko` (한국어)

## 문제 해결
- 메시지가 서버에 보이지 않으면 브로커 설정과 토픽이 일치하는지 확인하세요.
- 서버 로그(콘솔)에 MQTT 연결 또는 DB 오류 메시지가 출력됩니다.
- DB 직접 확인: `sqlite3 stress_data.db "SELECT * FROM sensor_log ORDER BY id DESC LIMIT 5;"`
