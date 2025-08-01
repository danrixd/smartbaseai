import pytest

from db.query_engine import QueryEngine
from config import tenant_config


def test_query_engine_postgres(monkeypatch):
    monkeypatch.setitem(tenant_config.TENANT_CONFIGS, 'pg', {
        'db_type': 'postgres',
        'db_config': {}
    })
    engine = QueryEngine('pg')
    result = engine.execute('SELECT 1')
    assert result['db'] == 'postgres'
    engine.close()


def test_query_engine_mysql(monkeypatch):
    monkeypatch.setitem(tenant_config.TENANT_CONFIGS, 'my', {
        'db_type': 'mysql',
        'db_config': {}
    })
    engine = QueryEngine('my')
    result = engine.execute('SELECT 2')
    assert result['db'] == 'mysql'
    engine.close()


def test_invalid_db_type(monkeypatch):
    monkeypatch.setitem(tenant_config.TENANT_CONFIGS, 'bad', {'db_type': 'unknown'})
    with pytest.raises(ValueError):
        QueryEngine('bad')
