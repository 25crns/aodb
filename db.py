"""Database helper: one short-lived MySQL connection per request.
Short-lived connections suit Vercel (serverless) and free cloud databases
that allow only a handful of simultaneous connections."""
import os
from contextlib import contextmanager

import pymysql
from pymysql.cursors import DictCursor
from dotenv import load_dotenv

load_dotenv()
ROOT = os.path.dirname(os.path.abspath(__file__))


def _connect(use_db=True):
    cfg = dict(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "airport_aodb"),
        charset="utf8mb4",
        cursorclass=DictCursor,
        connect_timeout=10,
        autocommit=False,
    )
    if not use_db:
        cfg.pop("database")   # used by load_db.py before the database exists
    ca = os.getenv("DB_SSL_CA")
    if ca:
        cfg["ssl"] = {"ca": os.path.join(ROOT, ca)}
    elif os.getenv("DB_SSL", "").lower() in ("1", "true", "yes"):
        cfg["ssl"] = {"check_hostname": False}
    return pymysql.connect(**cfg)


@contextmanager
def cursor(commit=True):
    """Everything inside one `with` block is ONE transaction:
    COMMIT if the block succeeds, ROLLBACK if any statement raises."""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_all(sql, params=None):
    with cursor(commit=False) as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def fetch_one(sql, params=None):
    with cursor(commit=False) as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def execute(sql, params=None):
    """INSERT / UPDATE / DELETE. Returns the new AUTO_INCREMENT id (if any)."""
    with cursor() as cur:
        cur.execute(sql, params)
        return cur.lastrowid
