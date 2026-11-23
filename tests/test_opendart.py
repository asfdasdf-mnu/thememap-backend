from io import BytesIO
import json
import urllib.error
from zipfile import ZipFile
import pytest
from app import opendart as dart

KEY = 'a' * 40
RECORD = '<list><corp_code>00123456</corp_code><corp_name>가상기업</corp_name><stock_code>005930</stock_code><modify_date>20260101</modify_date></list>'


def archive(xml, filename='CORPCODE.xml'):
    file = BytesIO()
    with ZipFile(file, 'w') as zipped:
        zipped.writestr(filename, xml.encode('utf-8'))
    return file.getvalue()


def test_identifiers_and_non_stock_filter():
    other = RECORD.replace('005930', '   ').replace('00123456', '00999999')
    result = dart.parse_companies(archive('<result>'+RECORD+other+'</result>'))
    assert result['companies'] == [dict(corp_code='00123456', corp_name='가상기업', stock_code='005930', modify_date='20260101')]
    assert result['skipped_without_stock_code'] == 1
    assert 'crtfc_key' not in json.dumps(result)
    assert result['source_url'] == dart.ENDPOINT


@pytest.mark.parametrize('change', [lambda s: s.replace('005930', '5930'),
    lambda s: s.replace('20260101', '20260230'), lambda s: s.replace('00123456', '123'),
    lambda s: s.replace('가상기업', ''), lambda s: s + s])
def test_reject_bad_identifiers(change):
    with pytest.raises(dart.DartError):
        dart.parse_companies(archive('<result>'+change(RECORD)+'</result>'))


@pytest.mark.parametrize('payload', [b'not XML', b'PKbadzip', archive('<result/>'),
    archive('<result>'+RECORD+'</result>', '../CORPCODE.xml'),
    archive('<!DOCTYPE result [<!ENTITY test "bad">]><result/>')])
def test_reject_invalid_response(payload):
    with pytest.raises(dart.DartError):
        dart.parse_companies(payload)


@pytest.mark.parametrize('status', ['010', '011', '012', '020', '800', '901', 'unknown'])
def test_provider_error_does_not_echo_message(status):
    with pytest.raises(dart.DartError) as error:
        dart.parse_companies(f'<result><status>{status}</status><message>{KEY}</message></result>'.encode())
    assert KEY not in str(error.value)


def test_size_limits(monkeypatch):
    monkeypatch.setattr(dart, 'MAX_XML', 10)
    with pytest.raises(dart.DartError, match='크기'):
        dart.parse_companies(archive('<result>'+RECORD+'</result>'))


@pytest.mark.parametrize('key', ['', 'short', 'a'*39+'\n'])
def test_invalid_key_prevents_request(monkeypatch, key):
    monkeypatch.setattr(dart.urllib.request, 'build_opener', lambda *a: pytest.fail('unexpected network'))
    with pytest.raises(dart.DartError):
        dart.download(key)


def test_download_timeout_and_key_redaction(monkeypatch):
    class Opener:
        def open(self, request, timeout):
            assert request.full_url == dart.ENDPOINT+'?crtfc_key='+KEY
            assert timeout == 30
            raise urllib.error.URLError('secret '+KEY)
    monkeypatch.setattr(dart.urllib.request, 'build_opener', lambda *a: Opener())
    with pytest.raises(dart.DartError) as error:
        dart.download(KEY)
    assert KEY not in str(error.value)
    assert error.value.__suppress_context__


def test_download_bound_and_success(monkeypatch):
    class Opener:
        def open(self, request, timeout):
            return BytesIO(b'12345')
    monkeypatch.setattr(dart.urllib.request, 'build_opener', lambda *a: Opener())
    assert dart.download(KEY) == b'12345'
    monkeypatch.setattr(dart, 'MAX_DOWNLOAD', 4)
    with pytest.raises(dart.DartError, match='크기'):
        dart.download(KEY)


def test_no_redirect():
    assert dart.NoRedirect().redirect_request(None, None, None, None, None, None) is None


def test_cli_saves_without_key_or_database(tmp_path, monkeypatch, capsys):
    path = tmp_path / 'review.json'
    monkeypatch.setenv('OPENDART_API_KEY', KEY)
    monkeypatch.setattr(dart, 'download', lambda key: archive('<result>'+RECORD+'</result>'))
    monkeypatch.setattr('sys.argv', ['opendart', '--output', str(path)])
    dart.main()
    data = json.loads(path.read_text())
    assert len(data['companies']) == 1
    assert data['fetched_at'] is not None
    assert KEY not in path.read_text()
    assert json.loads(capsys.readouterr().out)['database_changed'] is False
    original = path.read_text()
    with pytest.raises(SystemExit):
        dart.main()
    assert path.read_text() == original


def test_cli_missing_key_has_no_output(tmp_path, monkeypatch, capsys):
    path = tmp_path / 'review.json'
    monkeypatch.delenv('OPENDART_API_KEY', raising=False)
    monkeypatch.setattr('sys.argv', ['opendart', '--output', str(path)])
    with pytest.raises(SystemExit) as error:
        dart.main()
    assert error.value.code == 1
    assert not path.exists()
    assert 'OPENDART_API_KEY' in capsys.readouterr().err


def test_cli_offline_zip_needs_no_key_or_network(tmp_path, monkeypatch, capsys):
    source = tmp_path / 'corpcode.zip'
    target = tmp_path / 'review.json'
    source.write_bytes(archive('<result>'+RECORD+'</result>'))
    monkeypatch.delenv('OPENDART_API_KEY', raising=False)
    monkeypatch.setattr(dart, 'download', lambda *args: pytest.fail('unexpected network'))
    monkeypatch.setattr('sys.argv', ['opendart', '--input-zip', str(source), '--output', str(target)])
    dart.main()
    result = json.loads(target.read_text())
    assert len(result['companies']) == 1
    assert result['fetched_at'] is None
    assert result['converted_at']
    assert json.loads(capsys.readouterr().out)['database_changed'] is False


def test_cli_offline_zip_size_limit(tmp_path, monkeypatch, capsys):
    source = tmp_path / 'corpcode.zip'
    target = tmp_path / 'review.json'
    source.write_bytes(b'PKoversized')
    monkeypatch.setattr(dart, 'MAX_DOWNLOAD', 3)
    monkeypatch.setattr('sys.argv', ['opendart', '--input-zip', str(source), '--output', str(target)])
    with pytest.raises(SystemExit):
        dart.main()
    assert not target.exists()
    assert '크기 제한' in capsys.readouterr().err


def test_alphanumeric_stock_code():
    result = dart.parse_companies(archive('<result>'+RECORD.replace('005930', '0068Y0')+'</result>'))
    assert result['companies'][0]['stock_code'] == '0068Y0'


@pytest.mark.parametrize('code', ['0068y0', '0068-0', '0068 Y', '0068Y00'])
def test_reject_invalid_stock_code_characters(code):
    with pytest.raises(dart.DartError):
        dart.parse_companies(archive('<result>'+RECORD.replace('005930', code)+'</result>'))
