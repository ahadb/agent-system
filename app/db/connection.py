from psycopg2 import pool

from app.config import settings

_pool = None

def connect_params():
    """Build connection params from centralized app settings."""
    host = settings.PG_HOST
    port = settings.PG_PORT
    dbname = settings.PG_DATABASE
    user = settings.PG_USER
    password = settings.PG_PASSWORD
    sslmode = settings.PG_SSL_MODE
    return {
        "host": host,
        "port": port,
        "dbname": dbname,
        "user": user,
        "password": password,
        **({"sslmode": sslmode} if sslmode else {}),
    }


def _get_pool():
    """Lazy-initialize and return the connection pool."""
    global _pool
    if _pool is None:
        minconn = settings.PGPOOL_MIN
        maxconn = settings.PGPOOL_MAX
        _pool = pool.SimpleConnectionPool(minconn, maxconn, **connect_params())
    return _pool


def get_connection():
    """Return a connection from the pool. Close it to return it to the pool."""
    return _get_pool().getconn()


def close_pool():
    """Close all connections in the pool. Call on shutdown if needed."""
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None