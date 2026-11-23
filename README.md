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
python -m app.migrate
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

테이블 구조는 Alembic으로 관리합니다. 서버와 샘플 적재는 최신 DB 버전을 확인하며 임의로 테이블을 생성하지 않습니다. 실데이터 수집, 프론트 연동, 운영 배포는 아직 구현하지 않았습니다.

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


## DB 마이그레이션 (Alembic)

모든 명령은 저장소 루트에서 가상환경을 활성화하고 실행합니다. 기본 DB는 `sqlite:///./thememap.db`이며 PostgreSQL은 기존과 같이 `DATABASE_URL`로 지정합니다. 작업 전 서버를 종료하고 DB를 백업하세요.

### 새 DB

```sh
python -m app.migrate
python -m app.seed
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

`start-demo.cmd`, Docker API 시작, Dev Container 초기 구성에도 마이그레이션 명령을 포함했습니다. 이미 최신 버전이면 다시 실행해도 데이터를 변경하지 않습니다. 마이그레이션 이력이 없는 기존 DB는 자동 전환하지 않고 안내 오류로 중단합니다.

### 기존 DB를 처음 전환할 때

SQLite는 서버 종료 후 `thememap.db` 파일을 다른 이름으로 복사해 백업합니다. PostgreSQL은 `pg_dump` 등으로 백업한 뒤 진행합니다. 기존 DB와 같은 `DATABASE_URL`을 설정한 상태에서:

```sh
python -m app.migrate --adopt-existing
python -m alembic current
```

이 명령은 기존 구조를 고정된 `0001` 기준과 비교합니다. 일치하면 기존 데이터와 테이블을 유지하고 버전 이력만 붙입니다. 불일치하면 중단하므로 DB를 삭제하거나 강제로 `stamp`하지 말고 차이를 확인하세요. Docker의 기존 DB는 호스트에서 `docker compose run --rm api python -m app.migrate --adopt-existing` 실행 후 API를 다시 시작합니다.

### 앞으로 구조를 바꿀 때

모델 변경 후 `python -m alembic revision --autogenerate -m "변경 설명"`으로 변경 파일을 만들고 내용을 검토한 뒤 `python -m app.migrate`를 실행합니다. 자동 생성 결과는 데이터 변환과 일부 제약 변경을 놓칠 수 있으므로 검토해야 합니다. `migrations/baseline.py`와 `0001_initial.py`는 기존 DB 전환을 위한 고정 기준이므로 수정하지 않습니다.

`python -m alembic downgrade base`는 모든 테이블과 데이터를 삭제합니다. 테스트용 빈 DB의 롤백 검증에만 사용하세요. 실제 데이터가 있는 DB의 되돌리기는 백업 복구 및 해당 변경별 절차를 검토해야 합니다.

마이그레이션 테스트는 신규 생성, 재실행, 모델과의 일치, 롤백 후 재생성, 기존 데이터 유지, 구조 불일치 거부를 확인합니다. `TEST_DATABASE_URL`을 설정하면 해당 DB의 테이블을 삭제하고 검증하므로 반드시 폐기 가능한 테스트 전용 DB만 지정하세요.

## 실데이터 준비와 CSV 검증

공식 출처 검토 결과와 CSV 작성·입력 절차는 [DATA-SOURCES.md](docs/DATA-SOURCES.md)를 참고하세요. 실제 외부 데이터 수집은 아직 연결하지 않았습니다. 이미 등록된 테마에 종목과 근거를 연결하는 개발자용 입력 도구를 제공합니다.

```sh
# 기본은 검증만 수행 (DB 변경 없음)
python -m app.import_data examples/reviewed-data.sample.csv
# 검증한 파일을 일괄 입력
python -m app.import_data examples/reviewed-data.sample.csv --apply
```

예시는 가상 데이터이며 테마 ID 1이 필요합니다. 기존 DB 내용과 충돌하면 전체를 중단하며, 같은 파일 재입력은 기존 내용을 덮어쓰지 않습니다. 외부 출처 URL의 존재·내용·이용 권한은 별도 확인해야 합니다.

## OpenDART 종목 식별 정보 받기

OpenDART에서 발급한 인증키를 `OPENDART_API_KEY` 환경변수에 설정한 뒤, 저장소 루트에서 가상환경을 활성화하고 실행합니다. 키를 대화·Git·명령 인자로 보내지 마세요.

Windows 명령 프롬프트:

```bat
set OPENDART_API_KEY=발급받은40자리인증키
.venv\Scripts\python.exe -m app.opendart
```

PowerShell:

```powershell
$env:OPENDART_API_KEY='발급받은40자리인증키'
.\.venv\Scripts\python.exe -m app.opendart
```

macOS/Linux:

```sh
export OPENDART_API_KEY='발급받은40자리인증키'
python -m app.opendart
```

[OpenDART 인증키 신청](https://opendart.fss.or.kr/uss/umt/EgovMberInsertView.do)에서 발급 상태와 사용 IP 등을 확인하세요. 이 도구는 `.env` 파일을 자동으로 읽지 않습니다.

검토 결과는 Git 제외 경로인 `.local/dart-companies.json`에 저장합니다. DB와 기존 샘플은 변경하지 않습니다. 같은 파일이 있으면 덮어쓰지 않으므로 재수집 시 `--output .local/dart-companies-날짜.json`처럼 새 이름을 지정하세요.

종목 코드가 있는 항목의 `corp_code`(8자리), `stock_code`(6자리), `corp_name`, `modify_date`와 수집 시각·출처 URL을 저장합니다. 시장 구분·테마·연관 근거는 포함하지 않습니다. 원문 검토 후 필요한 종목을 골라 CSV에 옮기고 시장과 테마 근거를 별도로 확인해야 합니다. DART 변경일자는 수집 시각이나 상장 상태 확인 시각과 다릅니다.

요청은 30초 타임아웃이며 자동 재시도하지 않습니다. 다운로드 16MiB·XML 64MiB 제한을 두고 ZIP 파일을 디스크에 추출하지 않습니다. 오류 시 기존 검토 파일을 유지합니다. 네트워크 실패 시 연결을, 인증/IP·한도 오류 시 OpenDART 계정 설정을 확인하세요. 인증키나 원문 오류 메시지는 출력하지 않습니다.

공식 계약은 [고유번호 개발가이드](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019018)를 따릅니다. 테스트는 가상 ZIP/XML과 모의 네트워크 응답을 사용하며 실제 발급 키를 통한 응답 검증은 별도로 필요합니다.
