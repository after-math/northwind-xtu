from contextlib import contextmanager
import pymysql
from flask import current_app, g


def connect(config):
    options = dict(host=config['DB_HOST'], port=config['DB_PORT'],
                   user=config['DB_USER'], password=config['DB_PASSWORD'],
                   database=config['DB_NAME'], charset='utf8mb4',
                   cursorclass=pymysql.cursors.DictCursor, autocommit=True,
                   connect_timeout=5, read_timeout=20, write_timeout=20,
                   init_command="SET time_zone = '+08:00'")
    if config.get('DB_SSL_CA'):
        options.update(ssl_ca=config['DB_SSL_CA'], ssl_verify_cert=True, ssl_verify_identity=True)
    return pymysql.connect(**options)


def get_db():
    if 'db' not in g:
        g.db = connect(current_app.config)
    return g.db


def close_db(error=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def query(sql, args=(), one=False):
    with get_db().cursor() as cursor:
        cursor.execute(sql, args or None)
        return cursor.fetchone() if one else cursor.fetchall()


def execute(sql, args=()):
    with get_db().cursor() as cursor:
        cursor.execute(sql, args or None)
        return cursor.lastrowid


@contextmanager
def transaction():
    db = get_db()
    db.begin()
    try:
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
