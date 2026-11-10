"""Configuración central: conexión (variables de entorno), puerto y paleta de colores."""
import os
from dotenv import load_dotenv

load_dotenv()

SERVIDOR = os.getenv("DB_SERVER", r"(localdb)\MSSQLLocalDB")
BASE_DATOS = os.getenv("DB_NAME", "Tienda_Electrofernandez")
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
PUERTO = int(os.getenv("PORT", "8050"))
DEBUG = os.getenv("DEBUG", "0") == "1"
ULTIMO_MES = os.getenv("ULTIMO_MES") or None
UMBRAL_WAPE = 30.0  # criterio interno del proyecto

COLORES = {
    "marino": "#0B2A4A", "azul": "#1E6FD9", "celeste": "#6FA8F5", "claro": "#EAF2FF",
    "acento": "#F5A623", "ok": "#17A673", "alerta": "#E5484D", "texto": "#1F2D3D",
}
PALETA = ["#1E6FD9", "#0B2A4A", "#6FA8F5", "#F5A623", "#17A673", "#8FB8EA", "#3B4F6B"]
