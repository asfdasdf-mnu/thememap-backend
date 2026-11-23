import csv
import pytest
from app.import_data import COLUMNS
from app.verify_import import verify_import


def write_csv(path, overrides=None):
    row = dict(theme_id=7, stock_code='0068Y0', stock_name='가상 검증 기업', market='DEMO',
               stock_description='자동 테스트 전용', reason='가상 검증 근거',
               source_title='테스트 원문', source_url='https://example.com/report', is_sample='false')
    row.update(overrides or {})
    with path.open('w', encoding='utf-8-sig', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerow(row)


def test_reviewed_import_query_and_repeat(tmp_path):
    source = tmp_path / 'reviewed.csv'
    database = tmp_path / 'new.db'
    write_csv(source)
    result = verify_import(source, database, '검증 테마')
    assert result['preview']['applied'] is False
    assert result['applied']['new_stocks'] == result['applied']['new_links'] == 1
    assert result['repeated']['new_stocks'] == result['repeated']['new_links'] == 0
    assert result['theme_result']['theme']['id'] == 7
    assert result['theme_result']['items'][0]['code'] == '0068Y0'
    assert result['stock_results'][0]['themes'][0]['is_sample'] is False
    assert result['stock_results'][0]['themes'][0]['source_url'] == 'https://example.com/report'
    assert len(result['csv_sha256']) == 64


def test_existing_file_is_untouched(tmp_path):
    source = tmp_path / 'reviewed.csv'
    database = tmp_path / 'existing.db'
    write_csv(source)
    database.write_bytes(b'keep the existing data')
    with pytest.raises(FileExistsError):
        verify_import(source, database, '검증 테마')
    assert database.read_bytes() == b'keep the existing data'


@pytest.mark.parametrize('changes', [{'is_sample': 'true'}, {'source_url': ''}])
def test_unreviewed_input_does_not_create_database(tmp_path, changes):
    source = tmp_path / 'reviewed.csv'
    database = tmp_path / 'new.db'
    write_csv(source, changes)
    with pytest.raises(ValueError):
        verify_import(source, database, '검증 테마')
    assert not database.exists()


def test_multiple_themes_are_refused_before_creation(tmp_path):
    source = tmp_path / 'reviewed.csv'
    database = tmp_path / 'new.db'
    write_csv(source)
    content = source.read_text(encoding='utf-8-sig')
    source.write_text(content + content.splitlines()[1].replace('7,', '8,', 1) + '\n', encoding='utf-8')
    with pytest.raises(ValueError, match='one theme'):
        verify_import(source, database, '검증 테마')
    assert not database.exists()
