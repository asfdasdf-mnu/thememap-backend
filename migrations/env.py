from alembic import context
from app.database import Base, make_engine
from app import models  # register model metadata

config = context.config

def run(connection):
    context.configure(connection=connection, target_metadata=Base.metadata,
                      render_as_batch=connection.dialect.name == 'sqlite', compare_type=True)
    with context.begin_transaction():
        context.run_migrations()

if context.is_offline_mode():
    raise RuntimeError('Use online migrations with DATABASE_URL configured.')
elif config.attributes.get('connection') is not None:
    run(config.attributes['connection'])
else:
    engine = make_engine()
    with engine.connect() as connection:
        run(connection)
    engine.dispose()
