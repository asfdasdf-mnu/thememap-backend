import os
import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text
from app.database import Base, make_engine, session_factory
from app.migrate import configuration, migrate, require_current
from app.seed import seed


@pytest.fixture
def engine(tmp_path):
    engine = make_engine(os.getenv('TEST_DATABASE_URL') or f'sqlite:///{tmp_path / "migration.db"}')
    # TEST_DATABASE_URL must point to the disposable test database documented in README.
    with engine.begin() as connection:
        for table in ['theme_stocks', 'stocks', 'themes', 'alembic_version']:
            connection.execute(text(f'DROP TABLE IF EXISTS {table}'))
    yield engine
    engine.dispose()


def test_fresh_upgrade_repeat_and_downgrade(engine):
    migrate(engine)
    require_current(engine)
    with engine.connect() as connection:
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
    with session_factory(engine)() as session:
        seed(session)
    migrate(engine)
    with engine.begin() as connection:
        assert connection.scalar(text('SELECT count(*) FROM themes')) == 3
        command.downgrade(configuration(connection), 'base')
        assert set(inspect(connection).get_table_names()) <= {'alembic_version'}
    migrate(engine)
    require_current(engine)


def test_adopt_preserves_data_and_constraints(engine):
    Base.metadata.create_all(engine)  # simulate the pre-Alembic release
    with session_factory(engine)() as session:
        seed(session)
    with engine.begin() as connection:
        connection.execute(text("UPDATE themes SET description='user-edited' WHERE id=1"))
    with pytest.raises(RuntimeError, match='migration required'):
        require_current(engine)
    with pytest.raises(RuntimeError, match='unversioned'):
        migrate(engine)
    migrate(engine, adopt_existing=True)
    migrate(engine, adopt_existing=True)
    require_current(engine)
    with engine.connect() as connection:
        assert connection.scalar(text('SELECT description FROM themes WHERE id=1')) == 'user-edited'
        assert connection.scalar(text('SELECT count(*) FROM theme_stocks')) == 5
        assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []


def test_refuse_incompatible_legacy_database(engine):
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE themes (id INTEGER PRIMARY KEY, name TEXT)'))
        connection.execute(text("INSERT INTO themes VALUES (1, 'keep')"))
    with pytest.raises(RuntimeError, match='differs'):
        migrate(engine, adopt_existing=True)
    with engine.connect() as connection:
        assert connection.scalar(text('SELECT name FROM themes WHERE id=1')) == 'keep'
        assert MigrationContext.configure(connection).get_current_heads() == ()
