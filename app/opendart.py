"""Download OpenDART company identifiers to a local review file, without DB writes."""
import argparse
from datetime import datetime, timezone
from io import BytesIO
import json
import os
from pathlib import Path
import re
import tempfile
import zlib
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from zipfile import BadZipFile, ZipFile

ENDPOINT = 'https://opendart.fss.or.kr/api/corpCode.xml'
GUIDE = 'https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019018'
MAX_DOWNLOAD = 16 * 1024 * 1024
MAX_XML = 64 * 1024 * 1024
ERRORS = {'010': '인증키 등록 상태를 확인하세요.', '011': '인증키가 사용 중지되었습니다.',
          '012': '허용 IP를 확인하세요.', '020': '요청 한도를 초과했습니다. 나중에 다시 시도하세요.',
          '800': 'OpenDART 점검 중입니다.', '901': 'OpenDART 계정 상태를 확인하세요.'}


class DartError(ValueError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def download(api_key):
    if not re.fullmatch(r'[A-Za-z0-9]{40}', api_key or ''):
        raise DartError('OPENDART_API_KEY 환경변수에 발급받은 40자리 인증키를 설정하세요.')
    request = urllib.request.Request(ENDPOINT + '?crtfc_key=' + api_key)
    opener = urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(request, timeout=30) as response:
            payload = response.read(MAX_DOWNLOAD + 1)
    except (urllib.error.URLError, TimeoutError, OSError):
        # Exceptions can contain the full request URL and API key. Never echo them.
        raise DartError('OpenDART 요청 실패: 네트워크·HTTP 상태를 확인하세요. 자동 재시도하지 않습니다.') from None
    if len(payload) > MAX_DOWNLOAD:
        raise DartError('OpenDART 응답이 다운로드 크기 제한을 초과했습니다.')
    return payload


def parse_xml(payload):
    try:
        content = payload.decode('utf-8-sig')
        if '<!DOCTYPE' in content.upper() or '<!ENTITY' in content.upper():
            raise DartError('지원하지 않는 XML 선언입니다.')
        root = ET.fromstring(content)
    except (UnicodeDecodeError, ET.ParseError):
        raise DartError('OpenDART 응답이 올바른 UTF-8 XML이 아닙니다.') from None
    status = root.findtext('status')
    if status is not None and status != '000':
        # Do not include the provider message, which may reflect request values.
        raise DartError(ERRORS.get(status, 'OpenDART 오류 응답입니다. 공식 개발가이드의 상태 코드를 확인하세요.'))
    if root.tag != 'result':
        raise DartError('예상하지 못한 OpenDART XML 구조입니다.')
    return root


def parse_companies(payload):
    if not payload.startswith(b'PK'):
        parse_xml(payload)  # OpenDART errors may arrive as XML rather than ZIP.
        raise DartError('OpenDART 고유번호 ZIP 파일이 필요합니다.')
    try:
        with ZipFile(BytesIO(payload)) as archive:
            entries = archive.infolist()
            if len(entries) != 1 or entries[0].filename.upper() != 'CORPCODE.XML':
                raise DartError('ZIP에 CORPCODE.xml 파일 하나만 있어야 합니다.')
            if entries[0].file_size > MAX_XML:
                raise DartError('XML 크기 제한을 초과했습니다.')
            with archive.open(entries[0]) as file:
                xml = file.read(MAX_XML + 1)
            if len(xml) > MAX_XML:
                raise DartError('XML 크기 제한을 초과했습니다.')
    except (BadZipFile, RuntimeError, NotImplementedError, EOFError, zlib.error):
        raise DartError('OpenDART ZIP 파일을 읽을 수 없습니다.') from None
    root = parse_xml(xml)
    companies, seen_corp, seen_stock = [], set(), set()
    skipped = 0
    records = root.findall('list')
    if not records:
        raise DartError('회사 목록이 없는 고유번호 파일입니다.')
    for record in records:
        code = (record.findtext('stock_code') or '').strip()
        if not code:
            skipped += 1
            continue
        corp = (record.findtext('corp_code') or '').strip()
        name = (record.findtext('corp_name') or '').strip()
        date = (record.findtext('modify_date') or '').strip()
        if not (re.fullmatch(r'[0-9]{6}', code) and re.fullmatch(r'[0-9]{8}', corp)
                and name and len(name) <= 200 and re.fullmatch(r'[0-9]{8}', date)):
            raise DartError('고유번호 파일에 잘못된 회사 식별 정보가 있습니다.')
        try:
            datetime.strptime(date, '%Y%m%d')
        except ValueError:
            raise DartError('고유번호 파일의 변경일자가 잘못되었습니다.') from None
        if corp in seen_corp or code in seen_stock:
            raise DartError('고유번호 파일에 중복 식별자가 있습니다. 원문을 검토하세요.')
        seen_corp.add(corp)
        seen_stock.add(code)
        companies.append(dict(corp_code=corp, corp_name=name, stock_code=code, modify_date=date))
    return dict(source_url=ENDPOINT, guide_url=GUIDE,
                fetched_at=datetime.now(timezone.utc).isoformat(),
                skipped_without_stock_code=skipped,
                companies=sorted(companies, key=lambda item: item['stock_code']))


def save_review(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Publish a complete file without replacing an existing review file.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.dart-', delete=False) as file:
            temporary = file.name
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write('\n')
        os.link(temporary, path)
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='.local/dart-companies.json')
    args = parser.parse_args()
    if Path(args.output).exists():
        parser.exit(1, '출력 파일이 이미 있습니다. 다른 파일명을 지정하세요.\n')
    try:
        data = parse_companies(download(os.getenv('OPENDART_API_KEY', '')))
        save_review(args.output, data)
    except (DartError, OSError) as error:
        # Suppress chained exceptions and paths/URLs in OS errors.
        message = str(error) if isinstance(error, DartError) else '검토 파일을 저장할 수 없습니다.'
        parser.exit(1, message + '\n')
    print(json.dumps(dict(companies=len(data['companies']),
                          skipped_without_stock_code=data['skipped_without_stock_code'],
                          database_changed=False), ensure_ascii=False))


if __name__ == '__main__':
    main()
