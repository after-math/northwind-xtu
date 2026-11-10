import pytest

from app.db import connect


def config(**changes):
    return dict(DB_HOST='db.example', DB_PORT=3306, DB_USER='app', DB_PASSWORD='test-only',
                DB_NAME='northwind', **changes)


def test_tls_modes_keep_certificate_validation(monkeypatch):
    calls = []
    monkeypatch.setattr('app.db.pymysql.connect', lambda **kwargs: calls.append(kwargs))
    connect(config(DB_SSL_CA='trusted-ca.pem'))
    assert calls[-1]['ssl_verify_cert'] is True
    assert calls[-1]['ssl_verify_identity'] is True
    connect(config(DB_SSL_CA='trusted-ca.pem', DB_SSL_MODE='VERIFY_CA'))
    assert calls[-1]['ssl_verify_cert'] is True
    assert calls[-1]['ssl_verify_identity'] is False
    assert calls[-1]['ssl_ca'] == 'trusted-ca.pem'


@pytest.mark.parametrize('changes', [{'DB_SSL_MODE': 'DISABLED'}, {'DB_SSL_MODE': 'VERIFY_CA'}])
def test_invalid_tls_settings_cannot_connect(monkeypatch, changes):
    def unexpected_connection(**kwargs):
        raise AssertionError('无效的加密设置不能发起连接')
    monkeypatch.setattr('app.db.pymysql.connect', unexpected_connection)
    with pytest.raises(ValueError):
        connect(config(**changes))
