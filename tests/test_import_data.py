import csv
import os
import pytest
from sqlalchemy import event, select, text, func
from sqlalchemy.exc import IntegrityError
from app.database import make_engine, session_factory
from app.import_data import COLUMNS, ImportRow, import_rows, read_rows
from app.migrate import migrate
from app.models import Theme, Stock, ThemeStock


@pytest.fixture
def engine(tmp_path):
    engine = make_engine(os.getenv('TEST_DATABASE_URL') or f'sqlite:///{tmp_path / "import.db"}')
    with engine.begin() as connection:
        for table in ['theme_stocks', 'stocks', 'themes', 'alembic_version']:
            connection.execute(text(f'DROP TABLE IF EXISTS {table}'))
    migrate(engine)
    with session_factory(engine)() as session:
        session.add_all([Theme(id=1, name='샘플 테마', description='테스트'),
                         Theme(id=2, name='다른 테마', description='테스트')])
        session.commit()
    yield engine
    engine.dispose()


def row(**changes):
    values = dict(theme_id=1, stock_code='090001', stock_name='가상기업', market='DEMO',
                  stock_description='가상 예시', reason='가상 사업 근거', source_title='테스트 출처',
                  source_url=None, is_sample=True)
    values.update(changes)
    return ImportRow(**values)


def count(engine, model):
    with session_factory(engine)() as session:
        return session.scalar(select(func.count()).select_from(model))


def test_dry_run_apply_and_repeat(engine):
    rows = [row(), row(theme_id=2), row()]
    assert import_rows(engine, rows) == dict(rows=3, new_stocks=1, new_links=2, applied=False)
    assert count(engine, Stock) == count(engine, ThemeStock) == 0
    assert import_rows(engine, rows, apply=True)['new_links'] == 2
    assert import_rows(engine, rows, apply=True)['new_stocks'] == 0
    assert count(engine, Stock) == 1
    assert count(engine, ThemeStock) == 2
    with session_factory(engine)() as session:
        assert session.get(Stock, '090001').code == '090001'


@pytest.mark.parametrize('conflict', [row(stock_name='違う'), row(reason='違う')])
def test_conflict_inside_file_is_atomic(engine, conflict):
    with pytest.raises(ValueError, match='conflict'):
        import_rows(engine, [row(), conflict], apply=True)
    assert count(engine, Stock) == count(engine, ThemeStock) == 0


def test_missing_theme_and_existing_conflict(engine):
    with pytest.raises(ValueError, match='does not exist'):
        import_rows(engine, [row(), row(theme_id=999)], apply=True)
    assert count(engine, Stock) == 0
    import_rows(engine, [row()], apply=True)
    for changed in [row(stock_name='変更'), row(reason='変更')]:
        with pytest.raises(ValueError, match='conflict'):
            import_rows(engine, [row(stock_code='090002'), changed], apply=True)
    assert count(engine, Stock) == 1


def test_commit_failure_rolls_back_all(engine):
    def fail(*args):
        raise IntegrityError('test constraint failure', {}, Exception('test'))
    event.listen(ThemeStock, 'before_insert', fail)
    try:
        with pytest.raises(ValueError, match='nothing imported'):
            import_rows(engine, [row()], apply=True)
    finally:
        event.remove(ThemeStock, 'before_insert', fail)
    assert count(engine, Stock) == count(engine, ThemeStock) == 0


def write_csv(path, values):
    with path.open('w', encoding='utf-8-sig', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerow(values)


def test_csv_bom_and_real_source(tmp_path):
    path = tmp_path / 'data.csv'
    values = row(is_sample=False, source_url='https://example.com/report').model_dump(mode='json')
    values['is_sample'] = 'false'
    write_csv(path, values)
    result = read_rows(path)[0]
    assert result.is_sample is False
    assert result.stock_values()['code'] == '090001'
    values['source_url'] = ''
    write_csv(path, values)
    with pytest.raises(ValueError, match='line 2'):
        read_rows(path)


@pytest.mark.parametrize('field,value', [('stock_code', '90001'), ('stock_name', ' '),
    ('is_sample', '0'), ('source_url', 'javascript:alert(1)')])
def test_reject_invalid_csv(tmp_path, field, value):
    path = tmp_path / 'bad.csv'
    values = row().model_dump(mode='json')
    values.update(is_sample='true', source_url='')
    values[field] = value
    write_csv(path, values)
    with pytest.raises(ValueError, match='line 2'):
        read_rows(path)


def test_reject_empty_and_bad_shape(tmp_path):
    path = tmp_path / 'bad.csv'
    for content in ['', ','.join(COLUMNS)+'\n', ','.join(COLUMNS)+'\n1,a\n']:
        path.write_text(content)
        with pytest.raises(ValueError):
            read_rows(path)


def test_alphanumeric_csv_import(engine, tmp_path):
    path = tmp_path / 'alpha.csv'
    values = row(stock_code='0068Y0').model_dump(mode='json')
    values.update(is_sample='true', source_url='')
    write_csv(path, values)
    assert import_rows(engine, read_rows(path), apply=True)['new_stocks'] == 1
    with session_factory(engine)() as session:
        assert session.get(Stock, '0068Y0') is not None
