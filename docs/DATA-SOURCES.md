# 실데이터 도입 준비

확인일: 2026-11-24 (한국 시간). 현재 실제 종목·공시·시세 데이터를 수집하거나 DB에 넣은 상태는 아니다. 이번 단계는 출처 검토와 로컬 CSV 검증/입력 도구 준비다.

## 출처별 확인 결과와 결정

| 후보 | 공식 문서에서 확인한 내용 | 프로젝트 적용 판단 |
|---|---|---|
| OpenDART 고유번호 | 회사 고유번호·회사명·종목코드·최근변경일 제공. 인증키 필요 | 종목 식별 정보 후보. 시장 구분과 테마 분류를 이 파일만으로 만들지 않는다. |
| OpenDART 기업개황·공시검색 | 기업별 정보와 공시 목록 API 제공 | 공시 원문을 확인하고 테마 연관 이유를 직접 요약하는 근거 후보. 공시 존재가 테마 소속을 자동 입증하지는 않는다. |
| KRX Open API | 비상업 목적 제한(6조), 출처 표시(10조), 제3자 제공 제한(11조) 명시 | 공개 조회 API에 데이터를 넣기 전 해당 이용 방식의 허용 범위 확인 필요. 이번에는 수집·연동하지 않는다. |

근거 원문:

- [OpenDART 고유번호 개발가이드](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019018)
- [OpenDART 기업개황 개발가이드](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019002)
- [OpenDART 공시검색 개발가이드](https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001)
- [OpenDART 이용약관](https://opendart.fss.or.kr/intro/terms.do): 인증키 관리, 호출 허용량, 저작권 관련 조항 확인. API 접근 가능 여부와 자료 전체의 자유로운 재배포 허용은 별개로 확인해야 한다.
- [KRX Open API 이용약관](https://openapi.krx.co.kr/contents/OPP/INFO/OPPINFO002.jsp)

위 판단은 현재 프로젝트의 구현 방향이며 제공기관의 개별 허가나 법률 검토를 대신하지 않는다. 수집 자동화 전에 실제 이용 용도와 표시·재배포 범위를 확인하고, 해당 약관과 확인 날짜를 입력 파일과 함께 보관한다. 인증키를 CSV·Git·프론트 소스에 넣지 않는다.

## 데이터 준비 순서

1. 검토한 테마를 관리자 API로 등록하고 ID를 확인한다.
2. 종목 코드·이름·시장을 원문과 대조한다. OpenDART의 8자리 회사 고유번호와 6자리 종목 코드를 혼용하지 않는다.
3. 연관 이유는 원문을 검토해 직접 작성하고 문서명·공시일·관련 절을 `source_title`/`reason`에 넣는다. `source_url`은 근거 문서 주소를 사용한다.
4. 파일 옆에 수집일·검토자·원문/약관 주소·허용된 이용 범위를 별도 작업 기록으로 남긴다. 현재 DB가 검토자·수집일을 별도 컬럼으로 저장하지는 않는다.
5. 먼저 검증 명령으로 입력 예정 수를 확인하고, 확인한 파일을 `--apply`로 입력한다.

종목·테마 근거는 사람이 검토한 분류이며 거래소나 공시기관의 공식 테마 분류로 표시하지 않는다. 실시간 시세와 자동 투자 판단은 범위에 포함하지 않는다.

## CSV 입력 도구

저장소 루트에서 가상환경을 활성화하고, 마이그레이션을 완료한 DB를 대상으로 실행한다. 기본값은 검증만 수행하며 DB에 쓰지 않는다. URL 형식은 검사하지만 원문을 내려받거나 내용·권한을 자동 판정하지 않는다. 로컬 DB 접근 권한을 가진 개발자용 도구이며 HTTP 관리자 키를 사용하지 않는다.

```sh
python -m app.import_data examples/reviewed-data.sample.csv
python -m app.import_data examples/reviewed-data.sample.csv --apply
```

제공한 예시는 전부 가상 데이터다. 테마 ID 1이 필요하며 샘플 DB는 `python -m app.seed`로 준비할 수 있다. 실제 파일은 `.local/` 같은 Git 제외 경로에 보관한다.

CSV는 UTF-8 또는 UTF-8 BOM, 헤더 순서는 아래와 같다. 엑셀에서 코드 열을 텍스트로 지정해 앞자리 0을 보존한다. 쉼표·줄바꿈이 포함된 값은 CSV 규칙에 따라 큰따옴표로 감싼다.

```text
theme_id,stock_code,stock_name,market,stock_description,reason,source_title,source_url,is_sample
```

- `theme_id`: 이미 DB에 등록된 테마의 양의 정수 ID
- `stock_code`: 숫자 6자리, `stock_name`: 종목명, `market`: 검토한 시장 구분
- `stock_description`: 종목 설명(빈 값 가능)
- `reason`, `source_title`: 비어 있지 않은 근거·출처 이름
- `source_url`: HTTP(S) 주소. `is_sample=false`이면 필수
- `is_sample`: 반드시 `true` 또는 `false`. 실데이터는 `false`

검증 결과는 행 수·새 종목 수·새 연결 수·적용 여부를 JSON으로 출력한다. 동일 종목의 동일 정보와 동일 근거는 건너뛰며, 같은 코드나 연결에 다른 내용이 있으면 전체 입력을 중단한다. 기존 내용을 수정하려면 관리자 PUT API로 검토 후 수정한다. 중복 파일 재입력도 추가 데이터가 생기지 않는다.

한 파일은 최대 10,000행이며 전체를 먼저 검증한다. 저장 중 제약 충돌이 발생하면 종목과 근거 모두 롤백한다. 검증 후 DB가 변경되면 실제 적용 때 다시 충돌할 수 있으므로 적용 명령에서도 재검증한다. 샘플 데이터를 실데이터로 자동 전환하거나 테마를 자동 생성하지 않는다.

## 구현된 OpenDART 연결

`python -m app.opendart`로 고유번호 ZIP을 받아 로컬 검토용 JSON으로 변환할 수 있다. `OPENDART_API_KEY` 환경변수의 키를 사용하며 실제 API 요청이나 키 발급은 테스트에 포함하지 않는다. 실행 방법은 README의 OpenDART 절을 따른다. 기존의 “실제 데이터 미수집” 상태는 유효하며, 이 기능 추가만으로 실제 데이터 확보나 재배포 허가 확인이 완료되는 것은 아니다.
