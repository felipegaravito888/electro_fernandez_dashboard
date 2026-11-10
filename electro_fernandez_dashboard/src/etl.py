"""ETL: carga desde SQL Server y cálculo de los 7 KPIs (con filtros)."""
import pandas as pd
from .database import consultar

SQL_CATALOGO = """
SELECT p.id_producto, p.nombre AS producto, c.nombre_categoria AS categoria, p.precio
FROM PRODUCTO p INNER JOIN CATEGORIA c ON p.id_categoria = c.id_categoria
"""
SQL_VENTAS = """
SELECT v.id_venta, v.fecha_hora, v.forma_pago, ve.nombre AS vendedor,
       dv.id_producto, dv.cantidad, dv.subtotal
FROM DETALLE_VENTA dv
INNER JOIN VENTA v ON dv.id_venta = v.id_venta
INNER JOIN VENDEDOR ve ON v.id_vendedor = ve.id_vendedor
"""
# Supuesto: PEDIDO.id_proveedor y PROVEEDOR(id_proveedor, nombre). Ajusta si tus columnas difieren.
SQL_COMPRAS = """
SELECT dp.id_producto, pr.nombre AS proveedor, dp.cantidad, dp.subtotal
FROM DETALLE_PEDIDO dp
INNER JOIN PEDIDO pe ON dp.id_pedido = pe.id_pedido
INNER JOIN PROVEEDOR pr ON pe.id_proveedor = pr.id_proveedor
"""
SQL_COMPRAS_SIMPLE = "SELECT id_producto, cantidad, subtotal FROM DETALLE_PEDIDO"


def cargar_datos() -> dict:
    """Carga catálogo, ventas y compras ya unidos por producto/categoría."""
    cat = consultar(SQL_CATALOGO)
    ventas = consultar(SQL_VENTAS).merge(cat, on="id_producto", how="left")
    ventas["fecha_hora"] = pd.to_datetime(ventas["fecha_hora"])
    ventas["mes"] = ventas["fecha_hora"].dt.to_period("M").dt.to_timestamp()
    try:
        compras, hay_prov = consultar(SQL_COMPRAS), True
    except Exception:  # si las columnas de PEDIDO/PROVEEDOR difieren
        compras, hay_prov = consultar(SQL_COMPRAS_SIMPLE), False
        compras["proveedor"] = "Sin dato"
    compras = compras.merge(cat, on="id_producto", how="left")
    return {"catalogo": cat, "ventas": ventas, "compras": compras, "hay_proveedor": hay_prov}


def filtrar_ventas(df, ini, fin, cats, pagos, vends):
    """Aplica filtros de fecha, categoría, forma de pago y vendedor (listas vacías = todo)."""
    if ini:
        df = df[df["fecha_hora"] >= pd.to_datetime(ini)]
    if fin:
        df = df[df["fecha_hora"] < pd.to_datetime(fin) + pd.Timedelta(days=1)]
    if cats:
        df = df[df["categoria"].isin(cats)]
    if pagos:
        df = df[df["forma_pago"].isin(pagos)]
    if vends:
        df = df[df["vendedor"].isin(vends)]
    return df


def por_venta(df):
    """Una fila por venta (el total se calcula con las líneas filtradas)."""
    return df.groupby("id_venta").agg(fecha_hora=("fecha_hora", "first"), forma_pago=("forma_pago", "first"),
                                      vendedor=("vendedor", "first"), total=("subtotal", "sum")).reset_index()


def kpi1_ventas_mes(df):
    v = por_venta(df)
    v["periodo"] = v["fecha_hora"].dt.strftime("%Y-%m")
    r = v.groupby("periodo").agg(cantidad_ventas=("id_venta", "count"), total_vendido=("total", "sum"),
                                 ticket_promedio=("total", "mean")).reset_index()
    r["variacion_pct"] = r["total_vendido"].pct_change() * 100
    return r


def kpi2_categorias(df):
    r = df.groupby("categoria").agg(unidades_vendidas=("cantidad", "sum"), ingresos=("subtotal", "sum")).reset_index()
    r = r.sort_values("ingresos", ascending=False).reset_index(drop=True)
    r["participacion_pct"] = r["ingresos"] / (r["ingresos"].sum() or 1) * 100
    r["acumulado_pct"] = r["participacion_pct"].cumsum()
    r["ingreso_por_unidad"] = r["ingresos"] / r["unidades_vendidas"].replace(0, float("nan"))
    return r


def _abc(x):
    return "A" if x <= 80 else "B" if x <= 95 else "C"


def kpi3_productos(df, catalogo, cats):
    cat = catalogo[catalogo["categoria"].isin(cats)] if cats else catalogo
    ag = df.groupby("id_producto").agg(unidades_vendidas=("cantidad", "sum"), ingresos=("subtotal", "sum")).reset_index()
    r = cat.merge(ag, on="id_producto", how="left").fillna({"unidades_vendidas": 0, "ingresos": 0})
    r = r.sort_values("ingresos", ascending=False).reset_index(drop=True)
    r["participacion_pct"] = r["ingresos"] / (r["ingresos"].sum() or 1) * 100
    r["acumulado_pct"] = r["participacion_pct"].cumsum()
    r["clase_abc"] = r["acumulado_pct"].apply(_abc)
    r["ranking"] = r.index + 1
    return r


def kpi4_pagos(df):
    v = por_venta(df)
    r = v.groupby("forma_pago").agg(cantidad_ventas=("id_venta", "count"), dinero_recaudado=("total", "sum"),
                                    ticket_promedio=("total", "mean")).reset_index()
    r["participacion_pct"] = r["dinero_recaudado"] / (r["dinero_recaudado"].sum() or 1) * 100
    return r.sort_values("dinero_recaudado", ascending=False)


def kpi5_vendedores(df):
    v = por_venta(df)
    r = v.groupby("vendedor").agg(ventas_realizadas=("id_venta", "count"), total_vendido=("total", "sum"),
                                  ticket_promedio=("total", "mean")).reset_index()
    r["participacion_pct"] = r["total_vendido"] / (r["total_vendido"].sum() or 1) * 100
    return r.sort_values("total_vendido", ascending=False)


def kpi6_abastecimiento(df, compras, cats):
    c = compras[compras["categoria"].isin(cats)] if cats else compras
    co = c.groupby("categoria").agg(unidades_compradas=("cantidad", "sum"), costo_compras=("subtotal", "sum")).reset_index()
    ve = df.groupby("categoria").agg(unidades_vendidas=("cantidad", "sum"), ingresos_ventas=("subtotal", "sum")).reset_index()
    r = co.merge(ve, on="categoria", how="left").fillna({"unidades_vendidas": 0, "ingresos_ventas": 0})
    r["stock_estimado"] = r["unidades_compradas"] - r["unidades_vendidas"]
    r["rotacion_pct"] = r["unidades_vendidas"] / r["unidades_compradas"].replace(0, float("nan")) * 100
    r["costo_sobre_ingreso"] = r["costo_compras"] / r["ingresos_ventas"].replace(0, float("nan"))
    return r.sort_values("stock_estimado", ascending=False)


def kpi7_precios_proveedores(compras, cats):
    """Productos comprados a 2+ proveedores: precio unitario mínimo/máximo y diferencia."""
    c = compras[compras["categoria"].isin(cats)] if cats else compras
    c = c[c["cantidad"] > 0].copy()
    c["precio_unit"] = c["subtotal"] / c["cantidad"]
    g = c.groupby(["producto", "proveedor"]).agg(precio=("precio_unit", "mean"), unidades=("cantidad", "sum")).reset_index()
    g = g[g.groupby("producto")["proveedor"].transform("nunique") >= 2]
    filas = []
    for prod, x in g.groupby("producto"):
        lo, hi = x.loc[x["precio"].idxmin()], x.loc[x["precio"].idxmax()]
        filas.append({"producto": prod, "precio_min": lo["precio"], "precio_max": hi["precio"],
                      "proveedor_barato": lo["proveedor"], "proveedor_caro": hi["proveedor"],
                      "diferencia_pct": (hi["precio"] - lo["precio"]) / lo["precio"] * 100 if lo["precio"] else 0})
    cols = ["producto", "precio_min", "precio_max", "proveedor_barato", "proveedor_caro", "diferencia_pct"]
    return pd.DataFrame(filas, columns=cols).sort_values("diferencia_pct", ascending=False)
