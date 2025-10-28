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

## 보안/운영 고려사항
- 인증/인가: 사내 환경이면 방화벽과 네트워크 ACL로 보호, 추가로 API 키/MTLS 고려
- 비밀관리: `cert_password`는 환경변수/Windows Credential Manager 사용 권장
- 로그/감사: 서명 요청 해시, 타임스탬프, 요청 주체 기록 추가 권장
- 안정성: 서버 작업 디렉터리 주기적 청소, 파일 크기 제한 설정, 업로드 확장자 화이트리스트 유지
