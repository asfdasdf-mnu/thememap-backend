import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from app.main import create_app
from app.migrate import migrate
from app.models import ThemeStock, Theme
from app.seed import seed

@pytest.fixture
def client(tmp_path):
    app = create_app(os.getenv('TEST_DATABASE_URL') or f'sqlite:///{tmp_path / "test.db"}')
    migrate(app.state.engine)
    with TestClient(app) as client:
        with app.state.sessions() as session:
            seed(session)
        yield client

def test_search_pagination(client):
    result = client.get('/api/themes', params={'q': ' 반도 ', 'limit': 1}).json()
    assert result['total'] == 1
    assert result['items'][0]['id'] == 1
    assert client.get('/api/themes', params={'limit': 1, 'offset': 1}).json()['items'][0]['id'] == 2
    assert client.get('/api/themes', params={'offset': 100}).json()['items'] == []

def test_search_empty_and_literal_wildcards(client):
    for query in ['없는테마', '%', '_', "' OR 1=1 --"]:
        assert client.get('/api/themes', params={'q': query}).json()['items'] == []

def test_many_to_many_and_evidence(client):
    result = client.get('/api/stocks/900001').json()
    assert [t['id'] for t in result['themes']] == [1, 2]
    assert all(t['is_sample'] and t['source_url'] is None and t['reason'] for t in result['themes'])
    for id_ in [1, 2]:
        data = client.get(f'/api/themes/{id_}/stocks').json()
        assert any(s['code'] == '900001' for s in data['items'])
        assert data['theme']['stock_count'] == len(data['items'])

@pytest.mark.parametrize('path', ['/api/themes/999/stocks', '/api/stocks/000000'])
def test_not_found(client, path):
    assert client.get(path).status_code == 404

@pytest.mark.parametrize('path', ['/api/themes?limit=0', '/api/themes?limit=101', '/api/themes?offset=-1', '/api/themes/0/stocks', '/api/stocks/abc', '/api/stocks/12345'])
def test_invalid_input(client, path):
    assert client.get(path).status_code == 422

def test_seed_idempotent(client):
    with client.app.state.sessions() as session:
        seed(session)
        seed(session)
        assert session.scalar(select(func.count()).select_from(ThemeStock)) == 5

def test_duplicate_and_foreign_key_constraints(client):
    for theme_id, code in [(1, '900001'), (9999, '900001'), (1, '888888')]:
        with client.app.state.sessions() as session:
            session.add(ThemeStock(theme_id=theme_id, stock_code=code, reason='test', source_title='test', is_sample=True))
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()

def test_seed_preserves_existing_content(client):
    with client.app.state.sessions() as session:
        theme = session.get(Theme, 1)
        theme.description = '수정한 설명'
        session.commit()
        seed(session)
        assert session.get(Theme, 1).description == '수정한 설명'

def test_health_docs_contract(client):
    assert client.get('/health').json()['status'] == 'ok'
    assert client.get('/docs').status_code == 200
    schema = client.get('/openapi.json').json()
    assert '/api/themes/{theme_id}/stocks' in schema['paths']
    assert '가상 기업' in client.get('/').text

def test_cors(client):
    allowed = client.get('/api/themes', headers={'Origin': 'http://localhost:5173'})
    denied = client.get('/api/themes', headers={'Origin': 'https://untrusted.example'})
    assert allowed.headers['access-control-allow-origin'] == 'http://localhost:5173'
    assert 'access-control-allow-origin' not in denied.headers
