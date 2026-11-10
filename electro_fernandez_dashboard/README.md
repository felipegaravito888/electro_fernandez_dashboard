# ⚡ Dashboard Electro Fernández

Panel interactivo (Python · Dash · Plotly · Bootstrap) con los **7 KPIs** del proyecto de aula y un
**módulo predictivo** que responde la pregunta del informe:

> *¿Cuántas unidades se venderán por categoría en los próximos 30 días?*

## Requisitos
- Python 3.10+
- SQL Server / LocalDB con la base `Tienda_Electrofernandez`
- Driver **ODBC Driver 17 o 18 for SQL Server**

## Ejecución (VS Code)
```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env          # ajusta servidor/base si es necesario
python app.py
```
Se abre solo en el navegador: **http://127.0.0.1:8050**

## Estructura
```
app.py              Interfaz (layout + callbacks)
src/config.py       Variables de entorno, puerto, colores
src/database.py     Conexión SQL Server (driver automático)
src/etl.py          Consultas SQL y cálculo de los 7 KPIs
src/predictive.py   Ridge por categoría (WAPE) y K-means
src/charts.py       Gráficas Plotly
assets/style.css    Estilo azul/blanco
```

## Qué incluye
| Pestaña | Contenido |
|---|---|
| Resumen | Tarjetas de resumen + **KPI 1** ventas mensuales y ticket |
| Categorías y productos | **KPI 2** Pareto con *drill-down* (clic en una barra) · **KPI 3** ABC y Top 10 |
| Pagos y vendedores | **KPI 4** formas de pago · **KPI 5** vendedores |
| Abastecimiento | **KPI 6** compras vs ventas y rotación · **KPI 7** precios entre proveedores |
| Pronóstico y segmentos | Respuesta a la pregunta predictiva, **simulador** (se asignan valores a las variables predictoras: ventas de los 3 meses previos y mes objetivo), K-means y conclusión sin tecnicismos |

**Filtros** (aplican a los KPIs): rango de fechas, categoría, forma de pago y vendedor.

## Notas importantes
- El total de cada venta se calcula con la suma de `subtotal` de sus líneas, para que los filtros por categoría sean coherentes.
- Las compras (KPI 6 y 7) solo se filtran por categoría; muestran el histórico completo.
- **KPI 7** asume `PEDIDO.id_proveedor` y `PROVEEDOR(id_proveedor, nombre)`. Si tus columnas se llaman distinto, edita `SQL_COMPRAS` en `src/etl.py`. Si falla, el resto del dashboard sigue funcionando.
- El mes en curso se excluye del modelo si parece incompleto (o fíjalo con `ULTIMO_MES=2026-08` en `.env`).
- El modelo es un apoyo para planear compras: el margen de error (WAPE) se muestra siempre junto al pronóstico.

## Solución de problemas
- *No se pudo conectar*: revisa que LocalDB esté activo (`sqllocaldb start MSSQLLocalDB`) y el driver ODBC instalado.
- *Puerto ocupado*: cambia `PORT` en `.env`.
