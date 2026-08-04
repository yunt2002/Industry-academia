# 배포 안정화: Windows (NSSM) 및 자동 재시작 가이드

다음은 Windows에서 `monitor_main.py`(또는 `monitor_server.py`)를 안정적으로 실행하고 자동 재시작되도록 설정하는 방법입니다.

## 권장: NSSM(Non-Sucking Service Manager)을 사용
1. NSSM 다운로드: https://nssm.cc/download
2. 압축 해제 후 `nssm.exe` 위치를 확보
3. 관리자 권한 PowerShell을 열고 서비스 생성:

```powershell
# 예: 서비스 이름 stress-monitor
nssm install stress-monitor "C:\Path\To\.venv\Scripts\python.exe" "C:\Path\To\project\monitor_main.py"
# 작업 디렉터리 설정(옵션)
nssm set stress-monitor AppDirectory "C:\Path\To\project"
# 자동 재시작(기본적으로 실패 시 재시작 설정)
nssm set stress-monitor Start SERVICE_AUTO_START
nssm set stress-monitor RestartDelay 5000
nssm set stress-monitor AppStdout "C:\Path\To\project\logs\service_out.log"
nssm set stress-monitor AppStderr "C:\Path\To\project\logs\service_err.log"

# 서비스 시작
nssm start stress-monitor
```

4. 로그 파일을 확인하여 정상 시작 여부를 검증

## 대안: Windows 작업 스케줄러
- 간단한 경우 작업 스케줄러에 트리거(부팅 시 실행)와 실패 시 재시작(최대 재시도 설정) 규칙을 설정할 수 있습니다.

## 확인 및 모니터링
- `http://localhost:8765/health`로 서비스 헬스체크
- 서비스가 비정상 종료될 경우 NSSM이 자동으로 재시작합니다.

## Linux(참고)
- systemd 단위 파일을 작성해 `Restart=always`로 설정하면 동일한 효과를 얻습니다.

## 권장 로그/권한
- 로그 디렉터리를 만들고 서비스가 파일을 쓸 수 있도록 권한을 설정하세요.
- 가급적 가상환경의 절대 경로를 사용하세요.
