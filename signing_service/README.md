# Signing Service (Windows)

파이썬 기반 코드 서명 자동화 서비스.

구성:
- Server (Flask + Waitress): 파일 업로드 `/sign` 엔드포인트, Windows `signtool`로 서명
- Client (watchdog): 지정 폴더의 새 파일을 서버로 전송, 서명본 수신 후 출력 폴더에 저장
- Windows Service: pywin32 기반 서비스 엔트리 포함

## 설치 (Windows)

1) Python, pip, C++ Build Tools 설치
2) 가상환경 생성 후 의존성 설치
```bash
python -m venv venv
venv\Scripts\activate
pip install -r signing_service/requirements.txt
```

3) 서버/클라이언트 설정 수정
- `signing_service/server_config.json`
- `signing_service/client_config.json`

4) 서버 실행 (개발)
```bash
python -m signing_service.server.service --config signing_service/server_config.json
```

5) 클라이언트 실행 (개발)
```bash
python -m signing_service.client.service --config signing_service/client_config.json
```

## Windows Service 설치/관리
관리자 권한 PowerShell 또는 CMD에서 실행:
```bash
python signing_service/setup_windows_service.py --role server --action install --config C:\\signing_service\\server_config.json
python signing_service/setup_windows_service.py --role server --action start

python signing_service/setup_windows_service.py --role client --action install --config C:\\signing_service\\client_config.json
python signing_service/setup_windows_service.py --role client --action start
```

중지/삭제:
```bash
python signing_service/setup_windows_service.py --role server --action stop
python signing_service/setup_windows_service.py --role server --action remove
```

## EXE 빌드 (PyInstaller)

PyInstaller로 서버/클라이언트를 각각 단일 실행 파일(.exe)로 빌드할 수 있습니다. Windows PowerShell에서 다음을 수행하세요.

1) PyInstaller 설치
```bash
pip install pyinstaller
```

2) 서버 exe 빌드
```bash
pyinstaller -F -n signing-server \
  --add-data "signing_service/server_config.json;." \
  -p . -p signing_service \
  -i NONE \
  signing_service/server/service.py
```

3) 클라이언트 exe 빌드
```bash
pyinstaller -F -n signing-client \
  --add-data "signing_service/client_config.json;." \
  -p . -p signing_service \
  -i NONE \
  signing_service/client/service.py
```

- 위 명령은 기본 설정 JSON을 exe 내부 리소스로 포함합니다. 실행 시 같은 폴더에 JSON이 있으면 그 파일을 우선 사용합니다.
- 환경변수 `SIGNING_SERVICE_CONFIG_DIR`를 지정하면 그 경로의 JSON을 우선 탐색합니다.

4) 실행 예시
```powershell
./dist/signing-server.exe --config server_config.json
./dist/signing-client.exe --config client_config.json
```

### 서비스로 등록 (NSSM 권장)
PyInstaller로 만든 exe는 pywin32 서비스 프레임워크 없이도 NSSM을 통해 Windows 서비스로 손쉽게 등록할 수 있습니다.

1) NSSM 설치 후 관리자 PowerShell에서:
```powershell
nssm install SigningServer "C:\\path\\to\\signing-server.exe" --config C:\\signing_service\\server_config.json
nssm set SigningServer Start SERVICE_AUTO_START
nssm start SigningServer

nssm install SigningClient "C:\\path\\to\\signing-client.exe" --config C:\\signing_service\\client_config.json
nssm set SigningClient Start SERVICE_AUTO_START
nssm start SigningClient
```

2) 중지/삭제
```powershell
nssm stop SigningServer
nssm remove SigningServer confirm
nssm stop SigningClient
nssm remove SigningClient confirm
```

참고: 기존 `setup_windows_service.py`는 소스 형태(pywin32) 기반 서비스 설치에 유용합니다. exe 기반 배포에는 NSSM 방식이 간단합니다.

## 보안/운영 고려사항
- 인증/인가: 사내 환경이면 방화벽과 네트워크 ACL로 보호, 추가로 API 키/MTLS 고려
- 비밀관리: `cert_password`는 환경변수/Windows Credential Manager 사용 권장
- 로그/감사: 서명 요청 해시, 타임스탬프, 요청 주체 기록 추가 권장
- 안정성: 서버 작업 디렉터리 주기적 청소, 파일 크기 제한 설정, 업로드 확장자 화이트리스트 유지
