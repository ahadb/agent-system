import os
from psycopg2 import pool

_pool = None

# TODO: use a settings in config to intercept `.env` vars
def connect_params():
    """Build connection params from environment or defaults for local dev."""
    # Support both the preferred PG_* env vars and older/alternate names.
    # This keeps local setups consistent even if env keys differ.
    host = os.environ.get("PG_HOST") or os.environ.get("DB_HOST") or "localhost"
    port = int(os.environ.get("PG_PORT") or os.environ.get("DB_PORT") or "5433")
    dbname = (
        os.environ.get("PG_DATABASE")
        or os.environ.get("PG_NAME")
        or os.environ.get("DB_NAME")
        or "agent_system"
    )
    user = os.environ.get("PG_USER") or os.environ.get("DB_USER") or "ahadbokhari"
    password = os.environ.get("PG_PASSWORD") or os.environ.get("DB_PASSWORD") or ""
    sslmode = os.environ.get("PG_SSL_MODE") or os.environ.get("DB_SSL_MODE") or ""
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
        minconn = int(os.environ.get("PGPOOL_MIN", "1"))
        maxconn = int(os.environ.get("PGPOOL_MAX", "10"))
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