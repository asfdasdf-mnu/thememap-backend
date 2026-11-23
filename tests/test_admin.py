import pytest
from fastapi.testclient import TestClient
from app.main import create_app

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv('ADMIN_API_KEY', 'test-admin-key')
    with TestClient(create_app(f'sqlite:///{tmp_path / "admin.db"}')) as client:
        client.headers['X-Admin-Key'] = 'test-admin-key'
        yield client


def test_admin_auth(client, monkeypatch):
    for key in ['', 'wrong']:
        assert client.post('/api/admin/themes', json={'name': '테마'}, headers={'X-Admin-Key': key}).status_code == 401
    del client.headers['X-Admin-Key']
    assert client.post('/api/admin/themes', json={'name': '테마'}).status_code == 401
    monkeypatch.delenv('ADMIN_API_KEY')
    assert client.post('/api/admin/themes', json={'name': '테마'}).status_code == 503
    assert client.get('/api/themes').status_code == 200


def test_write_and_read_roundtrip(client):
    theme = client.post('/api/admin/themes', json={'name': ' 새 테마 '}).json()
    tid = theme['id']
    assert theme['name'] == '새 테마'
    assert client.post('/api/admin/stocks', json={'code': '900010', 'name': '가상기업', 'market': 'SAMPLE'}).status_code == 201
    path = f'/api/admin/themes/{tid}/stocks/900010'
    evidence = {'reason': '가상 연결', 'source_title': '샘플'}
    assert client.post(path, json=evidence).status_code == 201
    assert client.post(path, json=evidence).status_code == 409
    evidence.update(reason='수정한 근거', is_sample=False, source_url='https://example.com/report')
    assert client.put(path, json=evidence).status_code == 200
    assert client.put(f'/api/admin/themes/{tid}', json={'name': '수정 테마', 'description': '설명'}).status_code == 200
    assert client.put('/api/admin/stocks/900010', json={'name': '수정 기업', 'market': 'SAMPLE'}).status_code == 200
    result = client.get('/api/stocks/900010').json()
    assert result['name'] == '수정 기업'
    assert result['themes'][0]['reason'] == '수정한 근거'
    assert result['themes'][0]['name'] == '수정 테마'
    assert result['themes'][0]['is_sample'] is False
    assert client.get(f'/api/themes/{tid}/stocks').json()['theme']['stock_count'] == 1


def test_conflicts_validation_and_missing(client):
    assert client.post('/api/admin/themes', json={'name': '중복'}).status_code == 201
    assert client.post('/api/admin/themes', json={'name': '중복'}).status_code == 409
    for payload in [{'name': '   '}, {'name': '테마', 'unknown': True}, {'name': 'x' * 101}]:
        assert client.post('/api/admin/themes', json=payload).status_code == 422
    assert client.post('/api/admin/stocks', json={'code': 'ABC', 'name': '기업', 'market': 'SAMPLE'}).status_code == 422
    for payload in [
        {'reason': '근거', 'source_title': '출처', 'is_sample': False},
        {'reason': '근거', 'source_title': '출처', 'source_url': 'javascript:alert(1)'},
    ]:
        assert client.post('/api/admin/themes/1/stocks/900010', json=payload).status_code == 422
    assert client.put('/api/admin/themes/999', json={'name': '없음'}).status_code == 404
    evidence = {'reason': '근거', 'source_title': '샘플'}
    assert client.post('/api/admin/themes/999/stocks/900010', json=evidence).status_code == 404
    assert client.put('/api/admin/themes/999/stocks/900010', json=evidence).status_code == 404


def test_admin_preflight(client):
    response = client.options('/api/admin/themes', headers={
        'Origin': 'http://localhost:5173',
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'X-Admin-Key,Content-Type',
    })
    assert response.status_code == 200
