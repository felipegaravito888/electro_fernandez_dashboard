"""Figuras Plotly con estilo corporativo (azul/blanco)."""
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .config import COLORES as C, PALETA

ABC_COLOR = {"A": C["azul"], "B": C["acento"], "C": "#B8C4D6"}


def estilo(fig):
    fig.update_layout(template="plotly_white", font=dict(family="Inter, sans-serif", size=12, color=C["texto"]),
                      margin=dict(l=10, r=10, t=30, b=10), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", hoverlabel=dict(bgcolor="white", font_size=12),
                      legend=dict(orientation="h", y=1.13, x=0), separators=",.", colorway=PALETA)
    fig.update_xaxes(showgrid=False, linecolor="#D5DEEB")
    fig.update_yaxes(gridcolor="#E8EEF7", zeroline=False)
    return fig


def vacia(msg="Sin datos para los filtros seleccionados"):
    f = go.Figure()
    f.add_annotation(text=msg, showarrow=False, font=dict(size=14, color="#7A8BA3"))
    f.update_xaxes(visible=False)
    f.update_yaxes(visible=False)
    return estilo(f)


def ventas_mes(d):
    if d.empty:
        return vacia()
    f = make_subplots(specs=[[{"secondary_y": True}]])
    f.add_bar(x=d["periodo"], y=d["total_vendido"], name="Total vendido", marker_color=C["azul"],
              customdata=d["cantidad_ventas"], secondary_y=False,
              hovertemplate="%{x}<br>Vendido: $%{y:,.0f}<br>N° ventas: %{customdata}<extra></extra>")
    f.add_scatter(x=d["periodo"], y=d["ticket_promedio"], name="Ticket promedio", mode="lines+markers",
                  line=dict(color=C["acento"], width=3), secondary_y=True,
                  hovertemplate="Ticket: $%{y:,.0f}<extra></extra>")
    f.update_yaxes(title_text="Ventas ($)", secondary_y=False)
    f.update_yaxes(title_text="Ticket ($)", secondary_y=True, showgrid=False)
    return estilo(f)


def pareto(d):
    if d.empty:
        return vacia()
    f = make_subplots(specs=[[{"secondary_y": True}]])
    f.add_bar(x=d["categoria"], y=d["ingresos"], name="Ingresos", marker_color=C["azul"],
              hovertemplate="%{x}<br>Ingresos: $%{y:,.0f}<extra>clic para ver productos</extra>")
    f.add_scatter(x=d["categoria"], y=d["acumulado_pct"], name="% acumulado", mode="lines+markers",
                  line=dict(color=C["acento"], width=3), secondary_y=True)
    f.add_scatter(x=d["categoria"], y=[80] * len(d), name="Meta 80%", mode="lines",
                  line=dict(color=C["alerta"], dash="dot"), secondary_y=True)
    f.update_yaxes(title_text="Ingresos ($)", secondary_y=False)
    f.update_yaxes(title_text="% acumulado", range=[0, 105], secondary_y=True, showgrid=False)
    f.update_xaxes(tickangle=-35)
    return estilo(f)


def drill(d, cat):
    d = d[d["categoria"] == cat].nlargest(10, "ingresos")
    if d.empty or d["ingresos"].sum() == 0:
        return vacia("Esta categoría no tiene ventas en el periodo")
    f = px.bar(d, x="ingresos", y="producto", orientation="h", color="clase_abc", color_discrete_map=ABC_COLOR,
               hover_data={"unidades_vendidas": True, "precio": ":,.0f"})
    f.update_yaxes(autorange="reversed", title=None)
    f.update_xaxes(title="Ingresos ($)")
    return estilo(f)


def abc_curva(d):
    if d.empty:
        return vacia()
    f = px.scatter(d, x="ranking", y="acumulado_pct", color="clase_abc", color_discrete_map=ABC_COLOR,
                   category_orders={"clase_abc": ["A", "B", "C"]}, hover_data={"producto": True, "ranking": False})
    f.add_hline(y=80, line_dash="dot", line_color=C["alerta"])
    f.add_hline(y=95, line_dash="dot", line_color="#7A8BA3")
    f.update_xaxes(title="Productos ordenados por ingresos")
    f.update_yaxes(title="% acumulado de ingresos", range=[0, 102])
    f.update_traces(marker=dict(size=6))
    return estilo(f)


def top_productos(d):
    t = d.head(10)
    if t.empty:
        return vacia()
    f = px.bar(t, x="ingresos", y="producto", orientation="h", color="clase_abc", color_discrete_map=ABC_COLOR)
    f.update_yaxes(autorange="reversed", title=None)
    f.update_xaxes(title="Ingresos ($)")
    return estilo(f)


def pagos(d):
    if d.empty:
        return vacia()
    f = go.Figure(go.Pie(labels=d["forma_pago"], values=d["dinero_recaudado"], hole=0.6, customdata=d["ticket_promedio"],
                         marker=dict(colors=PALETA), textinfo="label+percent",
                         hovertemplate="%{label}<br>Recaudo: $%{value:,.0f}<br>Ticket: $%{customdata:,.0f}<extra></extra>"))
    f.update_layout(showlegend=False)
    return estilo(f)


def vendedores(d):
    if d.empty:
        return vacia()
    f = px.bar(d, x="total_vendido", y="vendedor", orientation="h", color="ticket_promedio",
               color_continuous_scale=["#CFE0FA", C["azul"], C["marino"]],
               hover_data={"ventas_realizadas": True, "participacion_pct": ":.1f"})
    f.update_yaxes(autorange="reversed", title=None)
    f.update_xaxes(title="Total vendido ($)")
    f.update_coloraxes(colorbar_title="Ticket")
    return estilo(f)


def abastecimiento(d):
    if d.empty:
        return vacia()
    f = make_subplots(specs=[[{"secondary_y": True}]])
    f.add_bar(x=d["categoria"], y=d["unidades_compradas"], name="Compradas", marker_color=C["marino"])
    f.add_bar(x=d["categoria"], y=d["unidades_vendidas"], name="Vendidas", marker_color=C["celeste"])
    f.add_scatter(x=d["categoria"], y=d["rotacion_pct"], name="Rotación %", mode="lines+markers",
                  line=dict(color=C["acento"], width=3), secondary_y=True)
    f.update_yaxes(title_text="Unidades", secondary_y=False)
    f.update_yaxes(title_text="Rotación %", secondary_y=True, showgrid=False)
    f.update_layout(barmode="group")
    f.update_xaxes(tickangle=-35)
    return estilo(f)


def proveedores(d):
    t = d.head(10)
    if t.empty:
        return vacia("Sin productos comprados a 2 o más proveedores")
    f = px.bar(t, x="diferencia_pct", y="producto", orientation="h", color="diferencia_pct",
               color_continuous_scale=["#CFE0FA", C["azul"], C["marino"]],
               hover_data={"proveedor_barato": True, "proveedor_caro": True, "precio_min": ":,.0f", "precio_max": ":,.0f"})
    f.update_yaxes(autorange="reversed", title=None)
    f.update_xaxes(title="Diferencia entre el proveedor más caro y el más barato (%)")
    f.update_coloraxes(showscale=False)
    return estilo(f)


def pronostico_categorias(d, sel):
    f = go.Figure(go.Bar(x=d["categoria"], y=d["pronostico"], marker_color=[C["acento"] if c == sel else C["azul"] for c in d["categoria"]],
                         error_y=dict(type="data", symmetric=False, array=d["alto"] - d["pronostico"],
                                      arrayminus=d["pronostico"] - d["bajo"], color="#7A8BA3"),
                         hovertemplate="%{x}<br>Se esperan ~%{y:,.0f} unidades<extra></extra>"))
    f.update_yaxes(title="Unidades próximos 30 días")
    f.update_xaxes(tickangle=-35)
    return estilo(f)


def historia(serie, cat, mes_obj, pred, bajo, alto, simulado):
    s = serie[serie["categoria"] == cat]
    f = go.Figure()
    f.add_scatter(x=s["mes"], y=s["unidades"], mode="lines+markers", name="Ventas reales", line=dict(color=C["azul"], width=3))
    f.add_scatter(x=[mes_obj, mes_obj], y=[bajo, alto], mode="lines", name="Rango probable",
                  line=dict(color=C["acento"], width=10), opacity=0.35)
    f.add_scatter(x=[mes_obj], y=[pred], mode="markers", name="Escenario simulado" if simulado else "Pronóstico",
                  marker=dict(size=15, color=C["acento"], line=dict(color="white", width=2)))
    f.update_yaxes(title="Unidades por mes")
    return estilo(f)


def segmentos(p):
    f = px.scatter(p, x="unidades_totales", y="ingresos_totales", color="segmento", hover_name="producto",
                   hover_data={"categoria": True, "precio": ":,.0f"}, opacity=0.8,
                   color_discrete_sequence=[C["azul"], C["acento"], C["marino"]])
    f.update_xaxes(title="Unidades vendidas")
    f.update_yaxes(title="Ingresos ($)")
    f.update_layout(legend_title_text="")
    return estilo(f)
