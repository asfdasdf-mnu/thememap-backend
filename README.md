# ThemeMap 백엔드

국내 주식 테마 정리 웹사이트의 조회 및 관리자 API 시제품입니다. 프론트엔드는 별도 개발하며, 현재 데이터는 **가상 기업 4개·테마 3개·연결 5개**입니다. 실제 종목·시세·공시를 수집한 결과가 아닙니다.

## 빠른 시연

Windows에서 Python 3.11 설치 후 `start-demo.cmd`를 실행합니다. 처음에는 인터넷이 필요합니다. 브라우저에서 http://127.0.0.1:8000/docs 를 엽니다. 종료는 실행 창에서 Ctrl+C입니다.

macOS/Linux 또는 직접 실행:

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.lock.txt
python -m app.seed
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

기본 DB는 SQLite이며 실행 폴더에 `thememap.db`가 생성됩니다. 별도 서버 없이 조회 로직을 검증하기 위한 모드입니다.

## PostgreSQL 환경

Docker Engine와 Compose가 설치된 환경에서:

```sh
docker compose up --build -d
docker compose exec api python -m app.seed
```

http://127.0.0.1:8000/docs 에 접속합니다. `docker compose down`으로 종료합니다. DB는 이름 있는 볼륨에 남습니다. `down -v`는 데이터를 지우므로 사용하지 마세요. Compose의 DB 암호는 개발용 예시이며 운영 배포에 사용하지 않습니다.

## 다른 PC에서 이어가기

소스와 테스트, 패키지 버전, Docker 설정을 함께 GitHub에 보관합니다. DB 파일·개인 키는 Git에 올리지 않습니다.

1. 이 저장소를 clone하고 VS Code의 Dev Containers로 폴더를 다시 엽니다. 또는 GitHub의 Code → Codespaces에서 새 환경을 엽니다.
2. `.devcontainer/devcontainer.json`이 Python·PostgreSQL 환경과 샘플 데이터를 준비합니다.
3. 터미널에서 `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`을 실행합니다.
4. Ports에서 8000 포트를 열고 `/docs`로 이동합니다. 포트 공개 범위는 Private을 유지합니다.
5. 수정 후 `python -m pytest -q` 실행 → commit → push 합니다. 다른 환경에서는 작업 전 pull 합니다.

Codespaces 실제 생성·실행은 아직 확인 전입니다. 사용량/계정 제한은 GitHub 화면에서 확인해야 합니다. Git으로 동기화되는 것은 코드이며 DB 내용이나 실행 중인 프로세스가 아닙니다. 새 환경은 샘플 DB로 시작합니다.

## API

| 요청 | 용도 |
|---|---|
| GET /health | 서버와 DB 연결 확인 |
| GET /api/themes?q=반도&limit=20&offset=0 | 테마 검색·페이지 조회 |
| GET /api/themes/1/stocks | 테마의 관련 종목과 이유·출처 |
| GET /api/stocks/900001 | 종목 정보와 연결된 모든 테마 |
| GET /docs | Swagger UI에서 요청 실행 |

없는 테마·종목은 404, 잘못된 파라미터는 422입니다. 검색 결과가 없으면 200과 빈 목록을 반환합니다. 검색어의 `%`, `_`는 와일드카드가 아닌 문자로 처리합니다. 프론트 기본 허용 주소는 localhost:5173이며 `CORS_ORIGINS` 환경변수로 변경합니다.

## 검증 및 한계

`python -m pytest -q`: 검색·다대다 조회·샘플 출처 표시·404/422·중복/외래키 제약·재실행·CORS 등 16개 검사. 테스트는 임시 SQLite DB를 기본 사용합니다. `TEST_DATABASE_URL`은 반드시 **테스트 전용 PostgreSQL DB**를 지정하세요.

GitHub Actions의 Linux 환경에서도 SQLite 및 PostgreSQL 17 검사가 모두 통과했습니다. 증빙: https://github.com/asfdasdf-mnu/thememap-backend/actions/runs/43922277701 (코드 커밋 829b248). Docker Compose 전체 부팅과 Codespaces 실제 실행은 별도 확인이 필요합니다.

초기 테이블 생성은 `create_all`입니다. 기존 테이블 구조를 변경하는 마이그레이션, 실데이터 수집, 프론트 연동, 운영 배포는 아직 구현하지 않았습니다. 관리자 API는 기존 테이블을 사용하므로 이번 변경에는 DB 마이그레이션이 필요하지 않습니다.

## 구조

- `app/models.py`: 테마·종목·연결 테이블
- `app/main.py`: 조회 API 및 오류 처리
- `app/schemas.py`: JSON 응답 계약
- `app/seed.py`: 충돌 검사 및 샘플 적재
- `tests/test_api.py`: 회귀 검사
- `docs/보고용-진행정리.md`: 발표 내용과 시연 순서
- `docs/openapi.json`: 프론트 담당자에게 전달할 API 계약

설정 참고: [FastAPI SQL 안내](https://fastapi.tiangolo.com/tutorial/sql-databases/), [FastAPI lifespan 테스트](https://fastapi.tiangolo.com/advanced/testing-events/), [Dev Container Compose 안내](https://containers.dev/guide/dockerfile).


## 관리자 등록·수정

서버 실행 전에 `ADMIN_API_KEY` 환경변수를 설정합니다. 미설정 시 관리자 요청은 503, 키 누락·불일치는 401입니다. 조회 API는 키 없이 사용할 수 있습니다. 키는 서버 환경변수에만 보관하며 프론트 소스나 Git에 넣지 않습니다. 공유 키 방식의 시제품이며 사용자별 로그인·권한·감사 기록은 다음 단계입니다.

Windows 명령 프롬프트에서 프로젝트 폴더를 연 뒤:

```bat
set ADMIN_API_KEY=여기에-직접-만든-긴-임의의-키
start-demo.cmd
```

macOS/Linux에서는 `export ADMIN_API_KEY='직접 만든 긴 임의의 키'` 설정 후 기존 실행 방법을 따릅니다. Docker Compose도 호스트의 `ADMIN_API_KEY`를 전달합니다. 변경 후 API 컨테이너를 다시 생성하세요.

`/docs`의 **Authorize**에 같은 키를 입력하고 관리자 API를 실행합니다.

| 요청 | 용도 |
|---|---|
| POST /api/admin/themes | 테마 등록: name, description(선택) |
| PUT /api/admin/themes/{theme_id} | 테마 이름·설명 전체 교체 |
| POST /api/admin/stocks | 종목 등록: code(숫자 6자리), name, market, description(선택) |
| PUT /api/admin/stocks/{code} | 종목 이름·시장·설명 전체 교체 (코드 유지) |
| POST /api/admin/themes/{theme_id}/stocks/{code} | 테마–종목 연결 및 근거 등록 |
| PUT /api/admin/themes/{theme_id}/stocks/{code} | 기존 연결의 근거 전체 교체 |

연관 근거 본문 예시:

```json
{"reason":"가상 기업의 테마 연결 예시", "source_title":"샘플 자료", "source_url":null, "is_sample":true}
```

실데이터(`is_sample=false`)는 HTTP(S) 출처 URL이 필수입니다. URL 존재나 이용 권한을 자동 검증하지는 않습니다. 등록 성공은 201, 수정 성공은 200, 없는 대상은 404, 중복은 409, 잘못된 입력은 422입니다. PUT은 부분 수정이 아니며 설명 생략 시 빈 문자열로 교체됩니다.

이번 관리자 변경은 SQLite에서 인증, 등록·수정 후 조회, 중복, 입력 검증, CORS를 포함한 전체 테스트 20개를 통과했습니다. PostgreSQL에서 이번 변경의 실행 결과는 GitHub Actions에서 별도로 확인해야 합니다.
