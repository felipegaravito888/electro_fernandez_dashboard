"""Dashboard Electro Fernández (Dash + Plotly). Ejecutar: python app.py"""
import threading
import webbrowser

import dash_bootstrap_components as dbc
import pandas as pd
from dash import Dash, Input, Output, dcc, html
from dash.exceptions import PreventUpdate

from src import charts as ch
from src import etl
from src.config import DEBUG, PUERTO, UMBRAL_WAPE
from src.predictive import Pronosticador, segmentar

FONT = "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap"
app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP, FONT],
           title="Electro Fernández | Dashboard", suppress_callback_exceptions=True)
server = app.server
CFG = {"displaylogo": False}
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def cop(x):
    return "$ " + f"{x:,.0f}".replace(",", ".")


def num(x):
    return f"{x:,.0f}".replace(",", ".")


def etiqueta(m):
    return f"{MESES[m.month - 1]} {m.year}"


# ------------------------------------------------------------------ datos y modelos
ERROR = None
try:
    DATA = etl.cargar_datos()
    VENTAS, CATALOGO, COMPRAS = DATA["ventas"], DATA["catalogo"], DATA["compras"]
    PRON = Pronosticador(VENTAS)
    PERFIL, K, SIL = segmentar(VENTAS)
    PREV = PRON.todas()
    STOCK = etl.kpi6_abastecimiento(VENTAS, COMPRAS, []).set_index("categoria")["stock_estimado"].to_dict()
except Exception as e:  # muestra un mensaje claro en vez de romper la app
    ERROR = f"{type(e).__name__}: {e}"


# ------------------------------------------------------------------ componentes
def kpi(id_, titulo, icono):
    return dbc.Col(dbc.Card(dbc.CardBody([
        html.Div(html.I(className=f"bi {icono}"), className="kpi-icon"),
        html.Div([html.Div(titulo, className="kpi-title"), html.H3(id=id_),
                  html.Div(id=id_ + "-sub", className="kpi-sub")])], className="kpi-body"), className="kpi"),
        xs=12, sm=6, lg=True)


def panel(titulo, gid, icono, alto=360, ins=None, **kw):
    cuerpo = [dcc.Loading(dcc.Graph(id=gid, config=CFG, style={"height": alto}), type="dot", color="#1E6FD9")]
    if ins:
        cuerpo.append(html.Div(id=ins, className="insight"))
    return dbc.Card([dbc.CardHeader([html.I(className=f"bi {icono} me-2"), titulo]), dbc.CardBody(cuerpo)],
                    className="panel")


def fila(*cols):
    return dbc.Row([dbc.Col(c, md=w, className="mb-3") for c, w in cols])


def tab_pronostico():
    cats = PRON.categorias
    b = PRON.base(cats[0])
    mx = int(max(b["serie"].max() * 2, 10))
    sl = lambda id_, v: dcc.Slider(0, mx, 1, value=int(round(v)), id=id_, tooltip={"placement": "bottom", "always_visible": True})
    meses = [PRON.siguiente + pd.DateOffset(months=i) for i in range(6)]
    seg = []
    if PERFIL is not None:
        for s, n in PERFIL["segmento"].value_counts().items():
            seg.append(dbc.Col(dbc.Card(dbc.CardBody([html.Div(s, className="kpi-title"), html.H3(f"{n} productos")]),
                                        className="kpi"), md=4, className="mb-2"))
    total_prev, total_ult = PREV["pronostico"].sum(), PREV["ultimo_mes"].sum()
    compradas = COMPRAS["cantidad"].sum()
    vendidas = VENTAS["cantidad"].sum()
    conclusion = (f"**Conclusión para la gerencia.** Para los próximos 30 días se esperan unas **{num(total_prev)} unidades** "
                  f"vendidas en toda la tienda (el último mes completo fueron {num(total_ult)}). "
                  f"Hoy se compran unas **{compradas / max(vendidas, 1):.1f} unidades por cada una que se vende**, "
                  "así que antes de pedir mercancía conviene revisar cuánto hay sin vender en bodega. "
                  "El pronóstico es una guía para planear las compras por categoría, no una cifra exacta: "
                  "sirve para decidir cuánto pedir, no para reemplazar el criterio del equipo.")
    return html.Div([
        dbc.Row([
            kpi("fc-k1", "Se venderán (30 días)", "bi-graph-up-arrow"), kpi("fc-k2", "Margen de error del modelo", "bi-bullseye"),
            kpi("fc-k3", "¿Es confiable?", "bi-patch-check")], className="mb-3 g-3"),
        dbc.Row([
            dbc.Col(dbc.Card([dbc.CardHeader([html.I(className="bi bi-sliders me-2"), "Simulador de escenarios"]),
                dbc.CardBody([
                    html.Label("Categoría", className="kpi-title"),
                    dcc.Dropdown(cats, cats[0], id="fc-cat", clearable=False, className="mb-3"),
                    html.Label("Mes a pronosticar", className="kpi-title"),
                    dcc.Dropdown([{"label": etiqueta(m), "value": m.strftime("%Y-%m-%d")} for m in meses],
                                 PRON.siguiente.strftime("%Y-%m-%d"), id="fc-mes", clearable=False, className="mb-3"),
                    html.Label("Unidades vendidas el mes pasado", className="kpi-title"), sl("fc-l1", b["l1"]),
                    html.Label("Hace 2 meses", className="kpi-title mt-2"), sl("fc-l2", b["l2"]),
                    html.Label("Hace 3 meses", className="kpi-title mt-2"), sl("fc-l3", b["l3"]),
                    dbc.Button([html.I(className="bi bi-arrow-counterclockwise me-2"), "Volver a datos reales"],
                               id="fc-reset", className="btn-reset mt-3 w-100")])], className="panel"), md=4, className="mb-3"),
            dbc.Col([html.Div(id="fc-respuesta", className="respuesta mb-3"),
                     panel("Historia y pronóstico de la categoría", "g-fc-hist", "bi-clock-history", 300)], md=8, className="mb-3")]),
        fila((panel("¿Cuántas unidades se venderán por categoría en los próximos 30 días?", "g-fc-all", "bi-boxes", 340), 12)),
        fila((panel("Segmentación de productos (K-means)", "g-km", "bi-diagram-3", 380), 12)),
        dbc.Row(seg, className="mb-3"),
        dcc.Markdown(conclusion, className="conclusion"),
    ])


def tab_kpi(*items):
    return html.Div(items)


def layout_ok():
    cats = sorted(CATALOGO["categoria"].dropna().unique())
    f = VENTAS["fecha_hora"]
    filtros = html.Div(dbc.Row([
        dbc.Col([html.Label("Rango de fechas"), dcc.DatePickerRange(id="f-fecha", start_date=f.min().date(), end_date=f.max().date(),
                 min_date_allowed=f.min().date(), max_date_allowed=f.max().date(), display_format="DD/MM/YYYY")], lg=3),
        dbc.Col([html.Label("Categoría"), dcc.Dropdown(cats, [], id="f-cat", multi=True, placeholder="Todas")], lg=3),
        dbc.Col([html.Label("Forma de pago"), dcc.Dropdown(sorted(VENTAS["forma_pago"].dropna().unique()), [], id="f-pago",
                 multi=True, placeholder="Todas")], lg=2),
        dbc.Col([html.Label("Vendedor"), dcc.Dropdown(sorted(VENTAS["vendedor"].dropna().unique()), [], id="f-vend",
                 multi=True, placeholder="Todos")], lg=2),
        dbc.Col(dbc.Button([html.I(className="bi bi-arrow-repeat me-2"), "Limpiar"], id="f-reset", className="btn-reset w-100"),
                lg=2, className="d-flex align-items-end")], className="g-2"), className="filtros")
    tabs = dbc.Tabs([
        dbc.Tab(tab_kpi(
            dbc.Row([kpi("k-ventas", "Ventas totales", "bi-cash-coin"), kpi("k-n", "N° de ventas", "bi-receipt"),
                     kpi("k-ticket", "Ticket promedio", "bi-bag-check"), kpi("k-unid", "Unidades vendidas", "bi-box-seam"),
                     kpi("k-rot", "Rotación de inventario", "bi-arrow-repeat")], className="mb-3 g-3"),
            fila((panel("KPI 1 · Evolución mensual de las ventas", "g-mes", "bi-graph-up", 380, "ins-mes"), 12))),
            label="Resumen", tab_id="t1"),
        dbc.Tab(tab_kpi(
            fila((panel("KPI 2 · Ingresos por categoría (Pareto) — haz clic en una barra", "g-pareto", "bi-tools", 380, "ins-cat"), 7),
                 (panel("Drill-down: productos de la categoría", "g-drill", "bi-search", 380), 5)),
            fila((panel("KPI 3 · Clasificación ABC de productos", "g-abc", "bi-sort-down", 340), 6),
                 (panel("Top 10 productos por ingresos", "g-top", "bi-trophy", 340), 6))),
            label="Categorías y productos", tab_id="t2"),
        dbc.Tab(tab_kpi(
            fila((panel("KPI 4 · Ventas según forma de pago", "g-pagos", "bi-credit-card", 360), 5),
                 (panel("KPI 5 · Desempeño de los vendedores", "g-vend", "bi-person-badge", 360, "ins-vend"), 7))),
            label="Pagos y vendedores", tab_id="t3"),
        dbc.Tab(tab_kpi(
            fila((panel("KPI 6 · Abastecimiento vs ventas (compras: histórico completo)", "g-abast", "bi-truck", 380, "ins-abast"), 12)),
            fila((panel("KPI 7 · Precios entre proveedores", "g-prov", "bi-lightning-charge", 360, "ins-prov"), 12))),
            label="Abastecimiento", tab_id="t4"),
        dbc.Tab(tab_pronostico(), label="Pronóstico y segmentos", tab_id="t5"),
    ], active_tab="t1")
    return html.Div([
        html.Div([html.Div(html.I(className="bi bi-lightning-charge-fill"), className="logo"),
                  html.Div([html.H1("Electro Fernández"),
                            html.P(f"Panel de decisiones · electricidad y electrónica · datos hasta {f.max():%d/%m/%Y}")])],
                 className="app-header"),
        dbc.Container([filtros, tabs, html.Div("Electro Fernández · Business Analytics · Dash + Plotly", className="pie")], fluid=True,
                      className="px-4")])


app.layout = layout_ok() if ERROR is None else dbc.Container([
    html.H3("No se pudo conectar a la base de datos", className="mt-5 text-danger"),
    html.P("Revisa SQL Server / LocalDB, el driver ODBC y el archivo .env (ver README)."), html.Pre(ERROR)])


# ------------------------------------------------------------------ callbacks
if ERROR is None:
    @app.callback([Output("f-fecha", "start_date"), Output("f-fecha", "end_date"), Output("f-cat", "value"),
                   Output("f-pago", "value"), Output("f-vend", "value")], Input("f-reset", "n_clicks"), prevent_initial_call=True)
    def limpiar(_):
        return VENTAS["fecha_hora"].min().date().isoformat(), VENTAS["fecha_hora"].max().date().isoformat(), [], [], []

    FILTROS = [Input("f-fecha", "start_date"), Input("f-fecha", "end_date"), Input("f-cat", "value"),
               Input("f-pago", "value"), Input("f-vend", "value")]
    SALIDAS = [Output(i, "children") for i in ["k-ventas", "k-ventas-sub", "k-n", "k-ticket", "k-unid", "k-rot", "k-rot-sub"]] + \
              [Output(i, "figure") for i in ["g-mes", "g-pareto", "g-abc", "g-top", "g-pagos", "g-vend", "g-abast", "g-prov"]] + \
              [Output(i, "children") for i in ["ins-mes", "ins-cat", "ins-vend", "ins-abast", "ins-prov"]]

    @app.callback(SALIDAS, FILTROS)
    def actualizar(ini, fin, cats, pagos, vends):
        df = etl.filtrar_ventas(VENTAS, ini, fin, cats, pagos, vends)
        if df.empty:
            return ["—", "", "—", "—", "—", "—", ""] + [ch.vacia()] * 8 + ["Sin datos para estos filtros."] * 5
        m, c = etl.kpi1_ventas_mes(df), etl.kpi2_categorias(df)
        p = etl.kpi3_productos(df, CATALOGO, cats)
        pg, vd = etl.kpi4_pagos(df), etl.kpi5_vendedores(df)
        ab = etl.kpi6_abastecimiento(df, COMPRAS, cats)
        pr = etl.kpi7_precios_proveedores(COMPRAS, cats) if DATA["hay_proveedor"] else pd.DataFrame()
        v = etl.por_venta(df)
        total, n, unid = v["total"].sum(), len(v), df["cantidad"].sum()
        comprado = ab["unidades_compradas"].sum()
        sub = f"Último mes: {m['variacion_pct'].iloc[-1]:+.1f}% vs anterior" if len(m) > 1 else ""
        rot = f"{unid / comprado * 100:.1f} %" if comprado else "N/D"
        rot_sub = f"{comprado / unid:.1f} compradas por cada vendida" if unid and comprado else ""
        mejor = m.loc[m["total_vendido"].idxmax()]
        n80 = int((c["acumulado_pct"].shift(fill_value=0) < 80).sum())
        t = vd.iloc[0]
        i_mes = f"Mejor mes: {mejor['periodo']} con {cop(mejor['total_vendido'])}."
        i_cat = f"{n80} de {len(c)} categorías generan el 80 % de los ingresos; la líder es {c.iloc[0]['categoria']} ({c.iloc[0]['participacion_pct']:.1f} %)."
        i_vend = f"{t['vendedor']} lidera con {t['participacion_pct']:.1f} % de las ventas ({num(t['ventas_realizadas'])} ventas)."
        if ab.empty:
            i_ab = "Sin datos de compras para estos filtros."
        else:
            w = ab.iloc[0]
            i_ab = (f"Se compraron {num(comprado)} unidades y se vendieron {num(ab['unidades_vendidas'].sum())}. "
                    f"Mayor excedente: {w['categoria']} (~{num(w['stock_estimado'])} unidades sin vender).")
        if not DATA["hay_proveedor"]:
            i_pr = "No se pudo leer la relación PEDIDO–PROVEEDOR; ajusta SQL_COMPRAS en src/etl.py (ver README)."
        elif pr.empty:
            i_pr = "No hay productos comprados a 2 o más proveedores con estos filtros."
        else:
            i_pr = (f"{len(pr)} productos se compran a 2+ proveedores; la diferencia promedio es {pr['diferencia_pct'].mean():.1f} %. "
                    f"El proveedor más barato más veces: {pr['proveedor_barato'].value_counts().index[0]}.")
        return [cop(total), sub, num(n), cop(total / n), num(unid), rot, rot_sub,
                ch.ventas_mes(m), ch.pareto(c), ch.abc_curva(p), ch.top_productos(p), ch.pagos(pg), ch.vendedores(vd),
                ch.abastecimiento(ab), ch.proveedores(pr) if not pr.empty else ch.vacia("Sin datos de proveedores"),
                i_mes, i_cat, i_vend, i_ab, i_pr]

    @app.callback(Output("g-drill", "figure"), [Input("g-pareto", "clickData")] + FILTROS)
    def drill(click, ini, fin, cats, pagos, vends):
        df = etl.filtrar_ventas(VENTAS, ini, fin, cats, pagos, vends)
        if df.empty:
            return ch.vacia()
        p = etl.kpi3_productos(df, CATALOGO, cats)
        if click and click.get("points"):
            cat = click["points"][0]["x"]
        else:
            cat = etl.kpi2_categorias(df).iloc[0]["categoria"]
        return ch.drill(p, cat)

    @app.callback([Output("fc-l1", "value"), Output("fc-l2", "value"), Output("fc-l3", "value"), Output("fc-l1", "max"),
                   Output("fc-l2", "max"), Output("fc-l3", "max"), Output("fc-mes", "value")],
                  [Input("fc-cat", "value"), Input("fc-reset", "n_clicks")])
    def reiniciar(cat, _):
        b = PRON.base(cat)
        mx = int(max(b["serie"].max() * 2, 10))
        return int(round(b["l1"])), int(round(b["l2"])), int(round(b["l3"])), mx, mx, mx, PRON.siguiente.strftime("%Y-%m-%d")

    @app.callback([Output("fc-respuesta", "children"), Output("g-fc-hist", "figure"), Output("g-fc-all", "figure")],
                  [Input("fc-cat", "value"), Input("fc-l1", "value"), Input("fc-l2", "value"), Input("fc-l3", "value"),
                   Input("fc-mes", "value")])
    def simular(cat, l1, l2, l3, mes):
        if None in (cat, l1, l2, l3, mes):
            raise PreventUpdate
        mes = pd.Timestamp(mes)
        pred = PRON.predecir(cat, l1, l2, l3, mes)
        e = (PRON.wape if PRON.wape == PRON.wape else 25) / 100
        bajo, alto = pred * (1 - e), pred * (1 + e)
        b = PRON.base(cat)
        simulado = (l1, l2, l3) != tuple(int(round(b[k])) for k in ("l1", "l2", "l3"))
        cuando = "en los próximos 30 días" if mes == PRON.siguiente else f"en {etiqueta(mes)}"
        stock = STOCK.get(cat)
        if stock is None:
            accion = ""
        elif stock >= pred:
            accion = f"Se estiman ~{num(stock)} unidades sin vender en bodega: **no hace falta comprar más por ahora**."
        else:
            accion = f"Se estiman ~{num(max(stock, 0))} unidades en bodega: conviene pedir unas **{num(pred - max(stock, 0))}**."
        txt = (f"Para **{cat}** se espera vender entre **{num(bajo)} y {num(alto)} unidades** {cuando}. {accion} "
               + ("*(Escenario simulado con tus valores.)*" if simulado else "*(Basado en las ventas reales.)*"))
        resp = [html.Div("Respuesta a la pregunta", className="kpi-title", style={"color": "#BBD3F5"}),
                html.H2(f"≈ {num(pred)} unidades"), dcc.Markdown(txt, style={"marginBottom": 0})]
        return resp, ch.historia(PRON.serie, cat, mes, pred, bajo, alto, simulado), ch.pronostico_categorias(PREV, cat)

    @app.callback([Output("fc-k1", "children"), Output("fc-k2", "children"), Output("fc-k3", "children"), Output("fc-k3-sub", "children"),
                   Output("fc-k1-sub", "children"), Output("fc-k2-sub", "children"), Output("g-km", "figure")], Input("fc-reset", "n_clicks"))
    def tarjetas_modelo(_):
        ok = "Sí, es una buena guía" if PRON.cumple and PRON.supera_base else "Úsalo con cautela"
        sub3 = f"Mejor que el promedio simple ({PRON.wape_base:.1f} %)" if PRON.supera_base else "No supera al promedio simple"
        return (num(PREV["pronostico"].sum()) + " und", f"± {PRON.wape:.0f} %", ok, sub3, "Todas las categorías",
                f"Meta del proyecto: ≤ {UMBRAL_WAPE:.0f} %",
                ch.segmentos(PERFIL) if PERFIL is not None else ch.vacia("Pocos productos para segmentar"))


def abrir():
    webbrowser.open(f"http://127.0.0.1:{PUERTO}")


if __name__ == "__main__":
    if not DEBUG:
        threading.Timer(1.5, abrir).start()
    app.run(host="127.0.0.1", port=PUERTO, debug=DEBUG)
