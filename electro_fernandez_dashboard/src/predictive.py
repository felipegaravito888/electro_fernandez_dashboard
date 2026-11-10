"""Modelo predictivo (Ridge por categoría, WAPE) y segmentación K-means de productos."""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, silhouette_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .config import ULTIMO_MES, UMBRAL_WAPE

NUM = ["lag_1", "lag_2", "lag_3", "promedio_3_meses", "promedio_6_meses", "promedio_historico",
       "tendencia", "mes_sin", "mes_cos", "indice_tiempo"]
CAT = ["categoria"]
ALPHAS = [0.01, 0.1, 1.0, 10.0, 50.0, 100.0]


def wape(y, p):
    """WAPE = suma|real - predicho| / suma real * 100."""
    y, p = np.asarray(y, float), np.asarray(p, float)
    return float(np.abs(y - p).sum() / y.sum() * 100) if y.sum() else float("nan")


def _modelo(alpha):
    pre = ColumnTransformer([("num", StandardScaler(), NUM), ("cat", OneHotEncoder(handle_unknown="ignore"), CAT)])
    return Pipeline([("pre", pre), ("reg", Ridge(alpha=alpha))])


def ultimo_mes_completo(df):
    """Último mes con datos completos (excluye el mes en curso si parece incompleto)."""
    if ULTIMO_MES:
        return pd.Timestamp(ULTIMO_MES + "-01")
    ult = df["fecha_hora"].max()
    mes = ult.to_period("M").to_timestamp()
    return mes - pd.DateOffset(months=1) if ult.day < ult.days_in_month - 3 else mes


class Pronosticador:
    """Entrena el Ridge con todo el histórico y permite simular escenarios."""

    def __init__(self, ventas):
        self.ultimo = ultimo_mes_completo(ventas)
        d = ventas[ventas["mes"] <= self.ultimo]
        self.categorias = sorted(d["categoria"].dropna().unique())
        meses = pd.date_range(d["mes"].min(), self.ultimo, freq="MS")
        self.anio0 = meses[0].year
        idx = pd.MultiIndex.from_product([self.categorias, meses], names=["categoria", "mes"])
        self.serie = (d.groupby(["categoria", "mes"])["cantidad"].sum().reindex(idx, fill_value=0)
                      .reset_index(name="unidades").sort_values(["categoria", "mes"]).reset_index(drop=True))
        self._features()
        self._validar()
        self.modelo = _modelo(self.alpha).fit(self.datos[NUM + CAT], self.datos["unidades"])
        self.siguiente = self.ultimo + pd.DateOffset(months=1)

    def _tiempo(self, mes):
        m = pd.DatetimeIndex(np.atleast_1d(mes))
        return (m.year - self.anio0) * 12 + m.month - 1, np.sin(2 * np.pi * m.month / 12), np.cos(2 * np.pi * m.month / 12)

    def _features(self):
        s = self.serie
        g = s.groupby("categoria")["unidades"]
        for k in (1, 2, 3):
            s[f"lag_{k}"] = g.shift(k)
        s["promedio_3_meses"] = g.transform(lambda x: x.shift(1).rolling(3).mean())
        s["promedio_6_meses"] = g.transform(lambda x: x.shift(1).rolling(6).mean())
        s["promedio_historico"] = g.transform(lambda x: x.shift(1).expanding().mean())
        s["tendencia"] = s["lag_1"] - s["lag_2"]
        s["indice_tiempo"], s["mes_sin"], s["mes_cos"] = self._tiempo(s["mes"])
        self.datos = s.dropna(subset=["lag_1", "lag_2", "lag_3", "promedio_3_meses",
                                      "promedio_6_meses", "promedio_historico"]).copy()

    def _caminar(self, alpha, meses):
        """Validación hacia adelante: para cada mes solo se entrena con meses anteriores."""
        salidas = []
        for m in meses:
            m = pd.Timestamp(m)
            tr, te = self.datos[self.datos["mes"] < m], self.datos[self.datos["mes"] == m].copy()
            if tr.empty or te.empty:
                continue
            te["pred"] = np.clip(_modelo(alpha).fit(tr[NUM + CAT], tr["unidades"]).predict(te[NUM + CAT]), 0, None)
            salidas.append(te)
        return pd.concat(salidas) if salidas else pd.DataFrame()

    def _validar(self):
        ms = sorted(self.datos["mes"].unique())
        n = 3 if len(ms) >= 7 else 1
        test, ajuste = ms[-n:], (ms[-2 * n:-n] if len(ms) >= 2 * n + 1 else [])
        self.alpha = 10.0
        if ajuste:
            res = []
            for a in ALPHAS:
                v = self._caminar(a, ajuste)
                if not v.empty:
                    res.append((wape(v["unidades"], v["pred"]), a))
            if res:
                self.alpha = min(res)[1]
        v = self._caminar(self.alpha, test)
        nan = float("nan")
        self.wape = wape(v["unidades"], v["pred"]) if not v.empty else nan
        self.wape_base = wape(v["unidades"], v["promedio_3_meses"]) if not v.empty else nan
        self.mae = mean_absolute_error(v["unidades"], v["pred"]) if not v.empty else nan
        self.cumple = bool(self.wape <= UMBRAL_WAPE)
        self.supera_base = bool(self.wape < self.wape_base)

    def base(self, cat):
        """Variables predictoras reales de la categoría (últimos 3 meses, promedio 6m e histórico)."""
        s = self.serie[self.serie["categoria"] == cat]["unidades"].to_numpy(float)
        pad = np.concatenate([np.zeros(3), s])
        return {"l1": pad[-1], "l2": pad[-2], "l3": pad[-3], "p6": s[-6:].mean(), "hist": s.mean(), "serie": s}

    def predecir(self, cat, l1, l2, l3, mes=None):
        """Unidades esperadas en el mes objetivo dado un escenario de ventas pasadas."""
        b = self.base(cat)
        idx, sn, cs = self._tiempo(mes or self.siguiente)
        fila = pd.DataFrame([{"lag_1": l1, "lag_2": l2, "lag_3": l3, "promedio_3_meses": (l1 + l2 + l3) / 3,
                              "promedio_6_meses": b["p6"], "promedio_historico": b["hist"], "tendencia": l1 - l2,
                              "mes_sin": sn[0], "mes_cos": cs[0], "indice_tiempo": idx[0], "categoria": cat}])
        return float(max(self.modelo.predict(fila[NUM + CAT])[0], 0))

    def todas(self):
        """Pronóstico base de los próximos 30 días para todas las categorías."""
        filas = []
        for c in self.categorias:
            b = self.base(c)
            p = self.predecir(c, b["l1"], b["l2"], b["l3"])
            e = (self.wape if self.wape == self.wape else 25) / 100
            filas.append({"categoria": c, "pronostico": p, "bajo": p * (1 - e), "alto": p * (1 + e),
                          "ultimo_mes": b["l1"]})
        return pd.DataFrame(filas).sort_values("pronostico", ascending=False).reset_index(drop=True)


def segmentar(ventas):
    """K-means por producto; elige k (2-6) con mayor Silhouette. Devuelve (perfil, k, silhouette)."""
    n_meses = max(ventas["mes"].nunique(), 1)
    p = ventas.groupby(["id_producto", "producto", "categoria", "precio"], as_index=False).agg(
        unidades_totales=("cantidad", "sum"), ingresos_totales=("subtotal", "sum"),
        meses_activos=("mes", "nunique"))
    p["promedio_mensual"] = p["unidades_totales"] / n_meses
    if len(p) < 10:
        return None, None, None
    vars_k = ["unidades_totales", "promedio_mensual", "ingresos_totales", "precio", "meses_activos"]
    X = StandardScaler().fit_transform(p[vars_k])
    mejor = max(((silhouette_score(X, KMeans(k, random_state=42, n_init=20).fit_predict(X)), k)
                 for k in range(2, 7)))
    sil, k = mejor
    p["cluster"] = KMeans(k, random_state=42, n_init=50).fit_predict(X)
    medias = p.groupby("cluster")[["precio", "unidades_totales"]].mean()
    c_valor = medias["precio"].idxmax()
    c_vol = medias.drop(index=c_valor)["unidades_totales"].idxmax() if k > 2 else None
    nombres = {c: "Baja rotación" for c in medias.index}
    nombres[c_valor] = "Alto valor"
    if c_vol is not None:
        nombres[c_vol] = "Alto volumen / bajo precio"
    p["segmento"] = p["cluster"].map(nombres)
    return p, k, sil
