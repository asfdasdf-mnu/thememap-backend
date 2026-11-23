"""Explicit schema setup; adopt a verified pre-Alembic database without changing data."""
import argparse
from pathlib import Path
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect
from .database import make_engine
from migrations.baseline import Base


def configuration(connection):
    config = Config(str(Path(__file__).resolve().parents[1] / 'alembic.ini'))
    config.attributes['connection'] = connection
    return config


def require_current(engine):
    with engine.connect() as connection:
        config = configuration(connection)
        current = MigrationContext.configure(connection).get_current_heads()
        if set(current) != set(ScriptDirectory.from_config(config).get_heads()):
            raise RuntimeError('Database migration required. Run: python -m app.migrate. '
                               'For pre-Alembic databases, back up and run: python -m app.migrate --adopt-existing')


def migrate(engine, adopt_existing=False):
    with engine.begin() as connection:
        config = configuration(connection)
        tables = set(inspect(connection).get_table_names()) - {'alembic_version'}
        current = MigrationContext.configure(connection).get_current_heads()
        if tables and not current:
            if not adopt_existing:
                raise RuntimeError('Existing unversioned database: back up first, then use --adopt-existing.')
            differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
            checks = inspect(connection).get_check_constraints('stocks') if 'stocks' in tables else []
            valid_check = any(c['name'] == 'stock_code_length' and
                              ''.join(c['sqltext'].split()).replace('::text', '').replace('(', '').replace(')', '') == 'lengthcode=6' for c in checks)
            inspector = inspect(connection)
            valid_primary_keys = all(
                inspector.get_pk_constraint(table.name)['constrained_columns'] ==
                [column.name for column in table.primary_key.columns]
                for table in Base.metadata.sorted_tables if table.name in tables)
            if differences or not valid_check or not valid_primary_keys:
                raise RuntimeError('Existing schema differs from baseline; no adoption performed.')
            command.stamp(config, '0001')
        command.upgrade(config, 'head')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adopt-existing', action='store_true')
    args = parser.parse_args()
    engine = make_engine()
    try:
        migrate(engine, args.adopt_existing)
    finally:
        engine.dispose()
    print('Database schema is current.')


if __name__ == '__main__':
    main()
