"""Validate a reviewed CSV; use --apply to insert stocks and theme evidence."""
import argparse
import csv
import json
from pathlib import Path
from pydantic import Field, ValidationError
from sqlalchemy.exc import IntegrityError
from .database import make_engine, session_factory
from .migrate import require_current
from .models import Stock, Theme, ThemeStock
from .schemas import StockCreate, EvidenceWrite

COLUMNS = ('theme_id', 'stock_code', 'stock_name', 'market', 'stock_description',
           'reason', 'source_title', 'source_url', 'is_sample')


class ImportRow(EvidenceWrite):
    theme_id: int = Field(ge=1)
    stock_code: str
    stock_name: str
    market: str
    stock_description: str

    def stock_values(self):
        return StockCreate(code=self.stock_code, name=self.stock_name, market=self.market,
                           description=self.stock_description).model_dump()

    def evidence_values(self):
        return self.model_dump(mode='json', include=set(EvidenceWrite.model_fields))


def read_rows(path):
    rows = []
    with Path(path).open(encoding='utf-8-sig', newline='') as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != list(COLUMNS):
            raise ValueError('CSV columns must match: ' + ','.join(COLUMNS))
        for line, values in enumerate(reader, 2):
            if len(rows) >= 10000:
                raise ValueError('CSV exceeds 10000 rows; split into smaller files.')
            if None in values or any(value is None for value in values.values()):
                raise ValueError(f'CSV line {line}: incorrect number of columns')
            if values['is_sample'] not in ('true', 'false'):
                raise ValueError(f'CSV line {line}: is_sample must be true or false')
            values['is_sample'] = values['is_sample'] == 'true'
            values['source_url'] = values['source_url'] or None
            try:
                row = ImportRow.model_validate(values)
                row.stock_values()
            except ValidationError as error:
                # Do not echo raw input values, which may contain private data.
                fields = ', '.join('.'.join(map(str, e['loc'])) or 'row' for e in error.errors())
                raise ValueError(f'CSV line {line}: invalid {fields}') from None
            rows.append(row)
    if not rows:
        raise ValueError('CSV must contain at least one data row')
    return rows


def import_rows(engine, rows, apply=False):
    require_current(engine)
    stocks, links = {}, {}
    with session_factory(engine)() as session:
        # Build the complete plan before writing anything, including during dry run.
        for number, row in enumerate(rows, 2):
            if session.get(Theme, row.theme_id) is None:
                raise ValueError(f'CSV line {number}: theme {row.theme_id} does not exist')
            stock_values = row.stock_values()
            existing = session.get(Stock, row.stock_code)
            previous = stocks.get(row.stock_code)
            if existing is not None:
                previous = {field: getattr(existing, field) for field in stock_values}
            if previous is not None and previous != stock_values:
                raise ValueError(f'CSV line {number}: conflicting stock {row.stock_code}')
            if existing is None:
                stocks[row.stock_code] = stock_values
            identity = (row.theme_id, row.stock_code)
            evidence = row.evidence_values()
            existing_link = session.get(ThemeStock, identity)
            previous_link = links.get(identity)
            if existing_link is not None:
                previous_link = {field: getattr(existing_link, field) for field in evidence}
            if previous_link is not None and previous_link != evidence:
                raise ValueError(f'CSV line {number}: conflicting theme-stock evidence')
            if existing_link is None:
                links[identity] = evidence
        result = dict(rows=len(rows), new_stocks=len(stocks), new_links=len(links), applied=apply)
        if apply:
            try:
                session.add_all(Stock(**values) for values in stocks.values())
                session.flush()
                session.add_all(ThemeStock(theme_id=tid, stock_code=code, **values)
                                for (tid, code), values in links.items())
                session.commit()
            except IntegrityError:
                session.rollback()
                raise ValueError('Database conflict; nothing imported. Refresh and validate again.') from None
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv_path')
    parser.add_argument('--apply', action='store_true', help='Insert after successful validation')
    args = parser.parse_args()
    try:
        rows = read_rows(args.csv_path)
        engine = make_engine()
        try:
            result = import_rows(engine, rows, args.apply)
        finally:
            engine.dispose()
    except (ValueError, OSError, csv.Error, RuntimeError) as error:
        parser.exit(1, f'Import failed: {error}\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
