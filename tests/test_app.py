import json
import pytest
from app import create_app, db

@pytest.fixture()
def app_instance(tmp_path):
    test_db = tmp_path / 'test.db'
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{test_db}'
    })
    with app.app_context():
        db.drop_all(); db.create_all()
    yield app

@pytest.fixture()
def client(app_instance):
    return app_instance.test_client()


def register_and_login(client, email='u1@example.com', password='pw'):
    r = client.post('/register', data={'email': email, 'password': password}, follow_redirects=True)
    assert r.status_code == 200
    r = client.get('/')
    assert r.status_code == 200


def test_login_required_for_api(client):
    r = client.get('/api/cards')
    assert r.status_code == 401
    assert r.get_json()['error'] == 'unauthorized'


def test_cfg_persist_per_user(client):
    register_and_login(client, 'a@example.com', 'pw')
    r = client.post('/api/cfg', json={'dailyNewLimit': 7, 'hideAnswer': False})
    assert r.status_code == 200
    r = client.get('/api/cfg'); j = r.get_json()
    assert j['dailyNewLimit'] == 7 and j['hideAnswer'] is False

    client.get('/logout')
    register_and_login(client, 'b@example.com', 'pw')
    j2 = client.get('/api/cfg').get_json()
    assert j2['dailyNewLimit'] == 20 and j2['hideAnswer'] is True


def test_add_and_list_roundtrip(client):
    register_and_login(client)
    # 缺字段
    r = client.post('/api/add', json={'word': ''})
    assert r.status_code == 400
    # 正常新增
    payload = {"word":"test","translation":"测试","example":"a test","phonetic":"tɛst","audioUrl":"","imageUrl":""}
    r = client.post('/api/add', json=payload)
    assert r.status_code == 200
    # 列表应该能看到
    arr = client.get('/api/cards').get_json()
    assert any(c['word']=='test' for c in arr)


def test_enrich_mock(client, monkeypatch):
    register_and_login(client)
    import app.routes.api as apimod
    monkeypatch.setattr(apimod, 'fetch_dictionary', lambda w: {"definition_en":"a mammal","example_en":"The dog barked.","phonetic":"/dɒg/","audio":"https://x/dog.mp3"})
    monkeypatch.setattr(apimod, 'translate_to_zh', lambda t: '家犬')
    monkeypatch.setattr(apimod, 'fetch_image', lambda w: 'https://x/dog.jpg')

    j = client.get('/api/enrich?word=dog').get_json()
    assert j['ok'] is True
    d = j['data']
    assert d['translation']=='家犬' and d['phonetic'] and d['audioUrl'].endswith('.mp3') and d['imageUrl'].endswith('.jpg')


def test_review_flow(client):
    register_and_login(client)
    client.post('/api/add', json={"word":"alpha","translation":"阿尔法"})
    cid = next(c['id'] for c in client.get('/api/cards').get_json() if c['word']=='alpha')
    assert client.post('/api/introduce', json={'id': cid, 'mode': 'tomorrow'}).status_code == 200
    assert client.post('/api/review', json={'id': cid, 'q': 5}).status_code == 200