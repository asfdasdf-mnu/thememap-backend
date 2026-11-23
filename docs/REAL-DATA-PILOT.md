# 반도체 실데이터 2종목 검증

2026-11-24(한국 시간)에 공식 기업개황과 2025 회계연도 사업보고서를 대조하고, 별도 SQLite DB에서 입력·조회 흐름을 확인했다. 기본 샘플 DB는 변경하지 않았다. 확인·요약·프로젝트 테마 분류는 Codex가 수행했으며 사용자 최종 검토는 아직 이루어지지 않았다.

## 선정 및 출처

| 종목 | 종목 코드 | DART 회사 고유번호 | 시장 확인 | 확인한 연간보고서 |
|---|---|---|---|---|
| 삼성전자 | 005930 | 00126380 | 기업개황 corp_cls=Y → KOSPI | 사업보고서(2025.12), 접수 20260310002820, 2026-03-10 |
| SK하이닉스 | 000660 | 00164779 | 기업개황 corp_cls=Y → KOSPI | 사업보고서(2025.12), 접수 20260317000635, 2026-03-17 |

기업개황과 공시검색 API 모두 정상 상태 `000`을 확인했다. 회사 고유번호는 이전에 받은 OpenDART 고유번호 파일과 대조했다. 시장 값은 확인 시점의 API 응답이며 보고서의 재무정보는 2025 회계연도에 해당한다. 최신 분기보고서까지 대조한 결과는 아니다.

- [기업개황 공식 개발가이드](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019002): `Y=유가증권시장`, `K=코스닥`, `N=코넥스`, `E=기타` 확인.
- 삼성전자 원문: [회사 IR에 공개된 2025 사업보고서 PDF](https://images.samsung.com/kdp/ir/business-report/2025_4Q_Interim_Business_Report_vF_kr.pdf#page=8), I.1 회사의 개요, DS 부문, 본문 4쪽(PDF 8쪽). 메모리 반도체, 설계, 위탁생산 사업을 근거로 프로젝트의 반도체 테마에 연결했다.
- SK하이닉스 원문: [KIND에 공개된 2025 사업보고서](https://kind.krx.co.kr/external/2026/03/17/000735/20260317002879/11011.htm), II.1 사업의 개요. DRAM·NAND 중심의 메모리 반도체 사업을 근거로 프로젝트의 반도체 테마에 연결했다.
- 접수번호 확인 링크: [삼성전자 DART](https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260310002820), [SK하이닉스 DART](https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260317000635). 본문 직접 열기는 이 환경에서 502가 발생하여 위 공식 재게시 원문으로 검토했다. 접수번호와 공시일은 OpenDART 공시검색 응답으로 별도 확인했다.

이는 사업 내용을 기준으로 작성한 프로젝트의 분류이며 제공기관의 공식 테마 지정이나 투자 추천이 아니다. 보고서 전체나 원본 API 응답을 배포하는 기능은 추가하지 않았다. 원문 재사용·공개 범위는 DATA-SOURCES.md의 조건 검토를 따른다.

## 실제 검증 결과

- CSV: 실종목 2행, 테마 ID 1, 이름 반도체, 두 행 모두 `is_sample=false`
- 미리보기: 새 종목 2개·새 연결 2개, DB 입력 없음
- 적용: 종목 2개·연관 근거 2개 저장
- 같은 CSV 재적용: 새 종목 0개·새 연결 0개
- `/api/themes/1/stocks`: 두 종목의 이름·코드·KOSPI·근거·원문 주소·샘플 아님 표시 확인
- `/api/stocks/005930`, `/api/stocks/000660`: 각각 반도체 테마 연결과 실제 근거 확인
- 검증 DB에는 위 테마 1개·실종목 2개·연결 2개만 존재하며 기존 가상 샘플과 섞지 않았다.

실행 중 생성한 파일은 `.local/`에 보관하고 Git에는 넣지 않았다.

- `semiconductor-companies-reviewed-20261124.json`: 필요한 회사·시장·접수번호 필드만 남긴 API 확인 기록(인증키 없음)
- `reviewed-semiconductor-20261124.csv`: 직접 요약한 설명과 근거, 원문 주소
- `real-semiconductor-pilot-20261124.db`: 별도 검증 SQLite DB
- `real-semiconductor-pilot-20261124-result.json`: 미리보기·입력·재입력·조회 결과 및 CSV SHA-256

## 다른 환경에서 재검증

이 기능이 포함된 브랜치에서 가상환경과 의존성을 준비한다. PR 미병합 상태에서는 `feat/real-semiconductor-pilot` 브랜치를 사용한다. 검토 CSV는 별도로 가져오거나 위 출처를 확인하여 DATA-SOURCES.md의 형식으로 작성한다.

```sh
python -m app.verify_import .local/reviewed-semiconductor-20261124.csv --database-path .local/reviewed-pilot-new.db --theme-name 반도체
```

이 명령은 CSV 검증 → 새 검증 DB 생성·마이그레이션 → CSV에 지정된 ID의 테마 생성 → 미리보기 → 적용 → 재적용 → 조회 API 대조를 수행하고 결과를 JSON으로 출력한다. 원문 내용이나 이용 권한, 분류의 적절성을 자동 판정하지 않는다.

검증용 도구는 SQLite와 한 테마의 실제 데이터 CSV를 대상으로 한다. 샘플 표시가 있는 행, 빈 출처 등 잘못된 입력, 여러 테마가 섞인 입력은 거부한다. 지정한 DB 파일이 이미 있으면 수정하지 않고 중단한다. 실행 중 실패한 경우 새로 만든 검증 DB가 남을 수 있으므로 원인을 확인한 뒤 다른 새 파일명으로 다시 실행한다. 기존 DB에 입력하려면 `app.import_data` 절차를 별도로 사용한다.

노트북에서 이 DB로 Swagger UI를 확인하려면 Windows 명령 프롬프트의 저장소 루트에서 아래처럼 실행한다. `start-demo.cmd`는 가상 샘플을 적재하므로 이 검증 DB에는 사용하지 않는다.

```bat
set DATABASE_URL=sqlite:///./.local/reviewed-pilot-new.db
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

서버 실행 후 http://127.0.0.1:8000/docs 에서 조회한다. 현재 클라우드 작업 환경의 파일이나 실행 프로세스가 노트북으로 자동 복사되는 것은 아니다.

검증에 사용한 CSV SHA-256: `378099d6e681c37df0db22bc2e38e37d0cb6d9b52b7acb89a32e1eae872861fb`. 원본 CSV와 API 응답, 검증 DB는 `.local/`에만 보관한다.
