"""Initial ThemeMap schema, frozen independently of application models."""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('themes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=False))
    op.create_table('stocks',
        sa.Column('code', sa.String(6), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('market', sa.String(20), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.CheckConstraint('length(code) = 6', name='stock_code_length'))
    op.create_table('theme_stocks',
        sa.Column('theme_id', sa.Integer(), sa.ForeignKey('themes.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('stock_code', sa.String(6), sa.ForeignKey('stocks.code', ondelete='CASCADE'), primary_key=True),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('source_title', sa.String(200), nullable=False),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('is_sample', sa.Boolean(), nullable=False))


def downgrade():
    op.drop_table('theme_stocks')
    op.drop_table('stocks')
    op.drop_table('themes')
