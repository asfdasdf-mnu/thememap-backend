"""Verify one reviewed theme CSV in a new, separate SQLite database."""
import argparse
import hashlib
import json
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import URL
from .database import make_engine, session_factory
from .import_data import read_rows, import_rows
from .main import create_app
from .migrate import migrate
from .models import Theme
from .schemas import ThemeWrite


def verify_import(csv_path, database_path, theme_name):
    rows = read_rows(csv_path)
    theme_ids = {row.theme_id for row in rows}
    if len(theme_ids) != 1:
        raise ValueError('Verification supports exactly one theme per CSV.')
    if any(row.is_sample for row in rows):
        raise ValueError('Use reviewed real-data rows with is_sample=false.')
    theme = ThemeWrite(name=theme_name)
    theme_id = next(iter(theme_ids))
    path = Path(database_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents a verification run from changing an existing DB.
    with path.open('xb'):
        pass
    url = URL.create('sqlite', database=str(path))
    engine = make_engine(url.render_as_string(hide_password=False))
    try:
        migrate(engine)
        with session_factory(engine)() as session:
            session.add(Theme(id=theme_id, name=theme.name,
                              description='원문을 검토하여 분류한 테마. 공식 테마 분류가 아닌 프로젝트의 판단입니다.'))
            session.commit()
        preview = import_rows(engine, rows)
        applied = import_rows(engine, rows, apply=True)
        repeated = import_rows(engine, rows, apply=True)
        if repeated['new_stocks'] or repeated['new_links']:
            raise ValueError('Repeated import unexpectedly added data.')
        with TestClient(create_app(url.render_as_string(hide_password=False))) as client:
            response = client.get(f'/api/themes/{theme_id}/stocks')
            if response.status_code != 200:
                raise ValueError('Theme lookup failed.')
            theme_result = response.json()
            expected = {row.stock_code for row in rows}
            if {item['code'] for item in theme_result['items']} != expected:
                raise ValueError('Theme lookup does not match the imported stock codes.')
            stocks = []
            for code in sorted(expected):
                response = client.get(f'/api/stocks/{code}')
                if response.status_code != 200:
                    raise ValueError('Stock lookup failed.')
                stock = response.json()
                if len(stock['themes']) != 1 or stock['themes'][0]['id'] != theme_id:
                    raise ValueError('Stock lookup does not match the imported theme.')
                if stock['themes'][0]['is_sample'] or not stock['themes'][0]['source_url']:
                    raise ValueError('Real-data evidence is missing from the stock lookup.')
                stocks.append(stock)
        return dict(csv_sha256=hashlib.sha256(Path(csv_path).read_bytes()).hexdigest(),
                    database_path=str(path), preview=preview, applied=applied, repeated=repeated,
                    theme_result=theme_result, stock_results=stocks)
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv_path')
    parser.add_argument('--database-path', required=True, help='A new SQLite file; existing files are refused')
    parser.add_argument('--theme-name', required=True)
    args = parser.parse_args()
    try:
        result = verify_import(args.csv_path, args.database_path, args.theme_name)
    except (ValueError, OSError, RuntimeError) as error:
        parser.exit(1, f'Verification failed: {error}\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
