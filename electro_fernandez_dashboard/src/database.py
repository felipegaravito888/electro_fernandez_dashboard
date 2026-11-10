"""Conexión a SQL Server (SQLAlchemy + pyodbc). Sin credenciales en el código."""
import pandas as pd
import pyodbc
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

from .config import SERVIDOR, BASE_DATOS, DB_USER, DB_PASSWORD

_engine = None


def elegir_driver() -> str:
    """Devuelve el mejor driver ODBC instalado para SQL Server."""
    preferidos = ["ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server",
                  "SQL Server Native Client 11.0", "SQL Server"]
    instalados = pyodbc.drivers()
    for d in preferidos:
        if d in instalados:
            return d
    raise RuntimeError("No se encontró ODBC Driver 17/18 para SQL Server.")


def get_engine():
    """Crea (una sola vez) el motor de conexión."""
    global _engine
    if _engine is None:
        driver = elegir_driver()
        auth = (f"UID={DB_USER};PWD={DB_PASSWORD};" if DB_USER else "Trusted_Connection=yes;")
        cadena = (f"DRIVER={{{driver}}};SERVER={SERVIDOR};DATABASE={BASE_DATOS};"
                  f"{auth}Encrypt=no;TrustServerCertificate=yes;")
        _engine = create_engine(URL.create("mssql+pyodbc", query={"odbc_connect": cadena}))
    return _engine


def consultar(sql: str) -> pd.DataFrame:
    """Ejecuta un SELECT y devuelve un DataFrame."""
    with get_engine().connect() as con:
        return pd.read_sql(text(sql), con)
