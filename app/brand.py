"""Marca personal de Davinson Arteaga aplicada a la demo, en dos temas que siguen al de Streamlit/sistema.

- **Día**: superficies y tinta del tema de VS Code "Davinson Día" (fondo #FAFBFC, barra #F1F3F6, bordes
  #E3E7EC, tinta #11151A, primario #005C56, enlaces #236997) + paleta `viz` Día de la skill `davinson-brand`.
- **Noche**: tokens Noche pastel de la skill `davinson-brand`.
- Paletas de gráficos validadas con `validate_palette.js` en su superficie (Día sobre #ffffff, Noche sobre
  #152a2f): todas las combinaciones usadas pasan (CVD ΔE ≥ 8,7; visión normal ≥ 17,7; contraste ≥ 3:1).
"""
from __future__ import annotations

import html
from dataclasses import dataclass

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

FONT_SANS = "IBM Plex Sans, Segoe UI, Helvetica, Arial, sans-serif"
FONT_MONO = "IBM Plex Mono, ui-monospace, Menlo, Consolas, monospace"
MINT, ABYSS = "#9ce0d9", "#043f52"
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


@dataclass(frozen=True)
class Theme:
    mode: str
    bg: str
    surface: str
    raised: str
    sidebar: str
    line: str             # grilla y bordes decorativos
    line_strong: str      # ejes y bordes de controles (≥ 3:1)
    grid_dot: str
    ink: str
    muted: str
    accent: str           # enlaces, delta positivo
    accent_soft: str
    negative: str
    negative_soft: str
    warning: str
    warning_soft: str
    logo: str
    role: str             # color de la línea de rol
    band: str             # relleno de bandas de referencia
    viz: tuple            # categóricas, orden fijo
    seq: tuple            # magnitud: del valor bajo (se funde con la superficie) al alto
    div: tuple            # divergente: durazno ← neutro → cielo (marca)


DIA = Theme(
    mode="light", bg="#FAFBFC", surface="#FFFFFF", raised="#F1F3F6", sidebar="#F1F3F6",
    line="#E3E7EC", line_strong="#8A9299", grid_dot="#E3E7EC", ink="#11151A", muted="#50585B",
    accent="#236997", accent_soft="#E2F2FD", negative="#8F3A14", negative_soft="#FDE9DF",
    warning="#6B5300", warning_soft="#FBF3D5", logo=ABYSS, role="#50585B", band="rgba(0,151,134,0.08)",
    viz=("#009786", "#8670c0", "#ba673f", "#2b88c0", "#b4608a", "#a28218"),
    seq=("#d9f6f1", "#abe5dd", "#7bcbc6", "#49aaaa", "#1e8691", "#056374", "#043f52"),
    div=("#a54a24", "#ce7951", "#ebb79d", "#e7eeee", "#a0cae7", "#549ac9", "#236997"),
)
NOCHE = Theme(
    mode="dark", bg="#0e2024", surface="#152a2f", raised="#1e343a", sidebar="#152a2f",
    line="#26434a", line_strong="#5a8990", grid_dot="#1d383e", ink="#e6f2f1", muted="#a2bfc2",
    accent="#a1dafc", accent_soft="#1c3645", negative="#ff9480", negative_soft="#3d2a24",
    warning="#ffc857", warning_soft="#353220", logo=MINT, role=MINT, band="rgba(156,224,217,0.10)",
    viz=("#25a897", "#927ccd", "#ca7b57", "#4b9bcf", "#c4759c", "#af8e2a"),
    seq=("#043f52", "#056374", "#1e8691", "#49aaaa", "#7bcbc6", "#abe5dd", "#d9f6f1"),
    div=("#a54a24", "#ce7951", "#ebb79d", "#2e4146", "#a0cae7", "#549ac9", "#236997"),
)


def theme() -> Theme:
    """Tema activo según Streamlit (que sigue al sistema o a la elección del usuario). Día por defecto."""
    t = getattr(st.context, "theme", None)
    return NOCHE if getattr(t, "type", None) == "dark" else DIA


def _logo(color: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 331 500" height="64" role="img" aria-label="Davinson Arteaga logo">
  <g fill="none" stroke="{color}" stroke-linecap="round" stroke-linejoin="round">
    <path d="M24 44V486M8 60L24 44L40 60M8 470L24 486L40 470" stroke-width="9"/>
    <path d="M300 271H312" stroke-width="9"/>
    <path d="M310 259L327 271L310 283Z" fill="{color}" stroke-width="3"/>
    <path d="M52 114V131Q52 151 72 151H180A120 120 0 0 1 180 391H72Q52 391 52 411V428" stroke-width="16"/>
    <path d="M32 183H245M38 272H286M32 364H243" stroke-width="4" stroke-linecap="butt" stroke-dasharray="6 4"/>
  </g></svg>"""


def _css(t: Theme) -> str:
    return f"""
<style>
:root {{
  --mint:{MINT}; --lavender:#d4c8fe; --peach:#fac3a5; --abyss:{ABYSS};
  --bg:{t.bg}; --surface:{t.surface}; --surface-raised:{t.raised}; --line:{t.line}; --line-strong:{t.line_strong};
  --grid-dot:{t.grid_dot}; --ink:{t.ink}; --ink-muted:{t.muted}; --accent:{t.accent}; --accent-soft:{t.accent_soft};
  --negative:{t.negative}; --negative-soft:{t.negative_soft}; --warning:{t.warning}; --warning-soft:{t.warning_soft};
  --radius-md:16px; --space-2:8px; --space-3:12px; --space-4:16px; --space-5:24px; --space-6:32px;
  --font-display:"Space Grotesk","IBM Plex Sans",system-ui,sans-serif;
  --font-sans:"IBM Plex Sans","Segoe UI",Helvetica,Arial,sans-serif;
  --font-mono:"IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace;
}}
.stApp {{ background-color:var(--bg);
  background-image:radial-gradient(var(--grid-dot) 1.5px, transparent 1.6px); background-size:24px 24px; }}
[data-testid="stHeader"] {{ background:transparent; }}
[data-testid="stSidebar"] > div:first-child {{ background:{t.sidebar}; border-right:1px solid var(--line); }}
.block-container {{ padding-top:2.5rem; max-width:1280px; }}
p, li {{ font-size:15px; line-height:24px; }}
h1, h2, h3, .da-h3 {{ text-wrap:balance; }}
[data-testid="stMarkdownContainer"] > p, [data-testid="stMarkdownContainer"] > ul, [data-testid="stMarkdownContainer"] > ol {{ max-width:78ch; }}
/* tarjetas y KPI */
.da-grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:var(--space-5); margin:4px 0 24px; }}
.da-card {{ background:var(--surface); border:1px solid var(--line); border-radius:var(--radius-md); padding:var(--space-5); }}
.da-card-pastel {{ border:0; }}
.da-overline {{ font:500 12px/16px var(--font-mono) !important; letter-spacing:.1em !important; text-transform:uppercase; color:var(--ink-muted); margin:0 !important; }}
.da-kpi {{ display:flex; flex-direction:column; gap:var(--space-2); }}
.da-kpi-value {{ font:600 clamp(26px, 2.4vw, 40px)/1.1 var(--font-display) !important; white-space:nowrap !important; letter-spacing:-.01em; font-variant-numeric:tabular-nums; margin:0 !important; color:var(--ink); }}
.da-kpi-foot {{ display:flex; flex-wrap:wrap; align-items:center; gap:var(--space-2); font:400 13px/20px var(--font-sans) !important; color:var(--ink-muted); }}
.da-delta {{ font:500 12px/16px var(--font-mono); padding:4px 10px; border-radius:999px; border:1px solid var(--line-strong); color:var(--ink); }}
.da-delta-up {{ color:var(--accent); background:var(--accent-soft); border-color:transparent; }}
.da-delta-down {{ color:var(--negative); background:var(--negative-soft); border-color:transparent; }}
.da-card-pastel .da-overline, .da-card-pastel .da-kpi-foot, .da-card-pastel .da-kpi-value {{ color:var(--abyss) !important; }}
.da-card-pastel .da-delta {{ background:rgba(255,255,255,.6); color:var(--abyss); border-color:transparent; }}
/* marco de gráfico */
[class*="st-key-frame"] {{ background:var(--surface); border:1px solid var(--line) !important; border-radius:var(--radius-md) !important; padding:var(--space-5) !important; }}
.da-h3 {{ font:600 18px/24px var(--font-sans) !important; color:var(--ink); margin:4px 0 2px !important; }}
.da-sub {{ font:400 13px/20px var(--font-sans) !important; color:var(--ink-muted); margin:0 0 4px !important; }}
.da-source {{ font:400 12px/16px var(--font-mono) !important; color:var(--ink-muted); margin:6px 0 0 !important; }}
/* tabla de texto: envuelve frases en vez de cortarlas */
.da-table {{ width:100%; border-collapse:collapse; margin:10px 0 4px; border:0 !important; }}
.da-table th {{ font:500 12px/16px var(--font-mono) !important; letter-spacing:.06em; text-transform:uppercase; color:var(--ink-muted);
  text-align:left; padding:8px 16px 8px 0 !important; border:0 !important; border-bottom:1px solid var(--line-strong) !important; background:transparent !important; }}
.da-table td {{ font:400 14px/22px var(--font-sans) !important; color:var(--ink); padding:10px 16px 10px 0 !important; vertical-align:top;
  border:0 !important; border-bottom:1px solid var(--line) !important; background:transparent !important; }}
.da-table td:first-child {{ font-weight:600 !important; }}
.da-table tr:last-child td {{ border-bottom:0 !important; }}
/* avisos: estado = color + palabra */
.da-callout {{ border-radius:var(--radius-md); padding:var(--space-4) var(--space-5); margin:8px 0 20px; color:var(--ink); }}
.da-callout p, .da-callout ul {{ margin:4px 0 0; max-width:78ch; }}
.da-callout ul {{ padding-left:20px; }}
.da-callout li {{ margin:2px 0; }}
.da-callout-info {{ background:var(--surface-raised); }}
.da-callout-warn {{ background:var(--warning-soft); }}
.da-callout-warn .da-overline {{ color:var(--warning); }}
/* sistema de líneas finas (estructura sin cajas) */
.da-rows {{ margin:8px 0 24px; border-top:1px solid var(--line-strong); }}
.da-row {{ display:grid; grid-template-columns:56px minmax(180px, 1fr) 2fr; gap:var(--space-5); padding:var(--space-4) 0;
  border-bottom:1px solid var(--line); align-items:baseline; }}
.da-row-n {{ font:600 28px/32px var(--font-display); color:var(--ink-muted); font-variant-numeric:tabular-nums; }}
.da-row-t {{ font:600 18px/24px var(--font-sans); color:var(--ink); }}
.da-row-b {{ font:400 15px/24px var(--font-sans); color:var(--ink); max-width:68ch; }}
.da-row-b small {{ display:block; color:var(--ink-muted); font-size:13px; line-height:20px; margin-top:4px; }}
.da-rail {{ display:grid; grid-template-columns:repeat(var(--n, 3), 1fr); gap:0; margin:8px 0 24px; }}
.da-stop {{ border-top:2px solid var(--ink); padding:var(--space-3) var(--space-5) 0 0; position:relative; }}
.da-stop::before {{ content:""; position:absolute; top:-6px; left:0; width:10px; height:10px; border-radius:999px; background:var(--ink); }}
.da-stop-k {{ font:600 32px/36px var(--font-display); color:var(--ink); margin:8px 0 2px; font-variant-numeric:tabular-nums; }}
.da-stop-o {{ font:500 13px/20px var(--font-sans); color:var(--ink-muted); }}
.da-stop-t {{ font:600 17px/24px var(--font-sans); color:var(--ink); margin:10px 0 4px; }}
.da-stop-b {{ font:400 15px/24px var(--font-sans); color:var(--ink); }}
.da-split {{ display:grid; grid-template-columns:1fr 1fr; margin:8px 0 24px; }}
.da-split > div {{ padding:var(--space-2) var(--space-6) var(--space-2) 0; }}
.da-split > div + div {{ border-left:1px solid var(--line-strong); padding-left:var(--space-6); }}
.da-q-who {{ font:500 13px/20px var(--font-sans); color:var(--ink-muted); }}
.da-q {{ font:600 24px/31px var(--font-display); color:var(--ink); margin:6px 0 10px; text-wrap:balance; letter-spacing:-.01em; }}
.da-q-b {{ font:400 15px/24px var(--font-sans); color:var(--ink); max-width:60ch; }}
@media (max-width: 900px) {{
  .da-row {{ grid-template-columns:40px 1fr; }} .da-row-b {{ grid-column:2; }}
  .da-rail, .da-split {{ grid-template-columns:1fr; }}
  .da-split > div + div {{ border-left:0; padding-left:0; border-top:1px solid var(--line-strong); padding-top:var(--space-4); }}
}}
/* chips por familia */
.da-tags {{ display:flex; flex-wrap:wrap; gap:var(--space-2); margin:8px 0 16px; }}
.da-tag {{ display:inline-flex; font:500 13px/16px var(--font-mono); padding:6px var(--space-3); border-radius:999px; color:var(--ink); border:1px solid var(--line-strong); }}
.da-tag-mint {{ background:var(--mint); border-color:var(--mint); color:var(--abyss); }}
.da-tag-lavender {{ background:var(--lavender); border-color:var(--lavender); color:var(--abyss); }}
.da-tag-peach {{ background:var(--peach); border-color:var(--peach); color:var(--abyss); }}
/* identidad */
.da-id {{ display:flex; flex-direction:column; align-items:flex-start; margin:4px 0 8px; }}
.da-name {{ font:600 18px/22px var(--font-display) !important; color:var(--ink); margin:12px 0 0 !important; }}
.da-role {{ font:500 14px/20px var(--font-sans) !important; color:{t.role} !important; margin:2px 0 0 !important; white-space:nowrap; }}
{'''/* botón primario mint (Noche): la tinta sobre un pastel siempre es abyss */
button[kind="primary"], button[kind="primary"] * { color:var(--abyss) !important; }''' if t.mode == "dark" else ""}
@media print {{ .stApp {{ background-image:none; }} }}
</style>
"""


def inject() -> Theme:
    t = theme()
    st.markdown(_css(t), unsafe_allow_html=True)
    return t


def identity() -> None:
    t = theme()
    st.sidebar.markdown(
        f'<div class="da-id">{_logo(t.logo)}<div><div class="da-name">Davinson Arteaga</div></div></div>',
        unsafe_allow_html=True)


# ---------- texto y números (español) ----------
def es(x: float, d: int = 1) -> str:
    s = f"{x:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".").replace("-", "−")


def mm(x: float, d: int = 1, sign: bool = False) -> str:
    return f"{'+' if sign and x > 0 else ''}{es(x / 1e6, d)} MM"


def pct(x: float, d: int = 0) -> str:
    return f"{es(x * 100, d)} %"


def quarter_label(q: str) -> str:
    """'2023Q2' → 'T2<br>2023' (sin rotar)."""
    return f"T{q[-1]}<br>{q[:4]}"


def es_table(df: pd.DataFrame, decimals: int = 1):
    """Tabla con formato colombiano (coma decimal, punto de miles) conservando el tipo numérico."""
    num = df.select_dtypes("number").columns
    fmt = {c: (lambda v, d=decimals: "" if pd.isna(v) else es(v, 0 if float(v).is_integer() else d)) for c in num}
    return df.style.format(fmt)


# ---------- componentes ----------
def kpi_row(items: list[dict]) -> None:
    """items: dict(overline, value, foot, delta=None, delta_kind=None|'up'|'down', pastel=False). Máx. 4."""
    cards = []
    for it in items[:4]:
        cls = "da-card da-kpi" + (" da-card-pastel" if it.get("pastel") else "")
        style_ = ' style="background:var(--mint)"' if it.get("pastel") else ""
        delta = ""
        if it.get("delta"):
            kind = {"up": " da-delta-up", "down": " da-delta-down"}.get(it.get("delta_kind"), "")
            delta = f'<span class="da-delta{kind}">{html.escape(it["delta"])}</span>'
        cards.append(f'<div class="{cls}"{style_}><div class="da-overline">{html.escape(it["overline"])}</div>'
                     f'<div class="da-kpi-value">{html.escape(it["value"])}</div>'
                     f'<div class="da-kpi-foot">{delta}<span>{html.escape(it["foot"])}</span></div></div>')
    st.markdown(f'<div class="da-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def callout(text_md: str, kind: str = "info") -> None:
    """Aviso. Info: superficie neutra, la frase en negrita hace de etiqueta. Warn: estado = color + palabra."""
    label = '<div class="da-overline">Atención</div>' if kind == "warn" else ""
    body = text_md if text_md.lstrip().startswith(("<ul", "<p")) else f"<p>{text_md}</p>"
    st.markdown(f'<div class="da-callout da-callout-{kind}">{label}{body}</div>', unsafe_allow_html=True)


def tags(groups: list[tuple[str, list[str]]]) -> None:
    """groups: [(familia: 'mint'|'lavender'|'peach'|'', [etiquetas])] en ese orden."""
    out = []
    for fam, labels in groups:
        cls = f"da-tag da-tag-{fam}" if fam else "da-tag"
        out += [f'<span class="{cls}">{html.escape(x)}</span>' for x in labels]
    st.markdown(f'<div class="da-tags">{"".join(out)}</div>', unsafe_allow_html=True)


def _month_ticks(fig: go.Figure) -> None:
    """Ejes de fecha con meses en español (ene y jul de cada año)."""
    xs = []
    for tr in fig.data:
        if getattr(tr, "x", None) is not None and tr.type in ("bar", "scatter"):
            xs += list(tr.x)
    if not xs or not all(len(str(x)) >= 7 and str(x)[4] == "-" for x in xs):
        return
    try:
        d = pd.to_datetime(pd.Series([str(x) for x in xs]), errors="raise")
    except Exception:
        return
    months = pd.period_range(d.min(), d.max(), freq="M")
    vals = [m for m in months if m.month in (1, 7)]
    fig.update_xaxes(tickvals=[m.start_time for m in vals], ticktext=[f"{MESES[m.month - 1]} {m.year}" for m in vals])


def style(fig: go.Figure, height: int = 360, ysuffix: str | None = None, right: int = 16,
          month_ticks: bool = True) -> go.Figure:
    """Anatomía de gráfico de marca: superficie del tema, grilla `line`, eje `line-strong`, ticks mono, un eje Y."""
    t = theme()
    fig.update_layout(
        height=height, margin=dict(l=8, r=right, t=36, b=8), separators=",.",
        paper_bgcolor=t.surface, plot_bgcolor=t.surface,
        font=dict(family=FONT_SANS, color=t.muted, size=12),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title=None,
                    font=dict(family=FONT_SANS, size=13, color=t.ink)),
        hoverlabel=dict(bgcolor=t.surface, bordercolor=t.line_strong, font=dict(family=FONT_SANS, color=t.ink, size=12)),
        bargap=0.3, barcornerradius=6,
    )
    fig.update_xaxes(showgrid=False, linecolor=t.line_strong, tickcolor=t.line_strong, ticks="outside", ticklen=4,
                     tickfont=dict(family=FONT_MONO, size=11, color=t.muted), title_font=dict(color=t.muted))
    fig.update_yaxes(gridcolor=t.line, gridwidth=1, zerolinecolor=t.line_strong, linecolor=t.line_strong,
                     tickfont=dict(family=FONT_MONO, size=11, color=t.muted), ticksuffix=ysuffix or "",
                     title_font=dict(color=t.muted), tickformat=",~f")
    if month_ticks:
        _month_ticks(fig)
    ys = [v for tr in fig.data if tr.type == "bar" and tr.orientation != "h" and tr.y is not None
          for v in tr.y if isinstance(v, (int, float)) and v == v]
    if ys and min(ys) >= 0:                       # solo positivos: la línea del eje X ya es la base
        fig.update_yaxes(zeroline=False)
    fig.update_traces(selector=dict(type="bar"), marker_line=dict(color=t.surface, width=2))
    fig.update_traces(selector=dict(type="scatter"), line=dict(width=2))
    return fig


def end_labels(fig: go.Figure) -> go.Figure:
    """Etiqueta directa selectiva: el nombre de cada serie en su último punto (texto en tinta, no en el color)."""
    t = theme()
    for tr in fig.data:
        if tr.type != "scatter" or tr.x is None or len(tr.x) == 0 or tr.showlegend is False:
            continue
        fig.add_annotation(x=list(tr.x)[-1], y=list(tr.y)[-1], text=tr.name, showarrow=False, xanchor="left", xshift=8,
                           font=dict(family=FONT_SANS, size=12, color=t.ink))
    return fig


def _head(overline: str, title: str, subtitle: str) -> str:
    """Etiqueta opcional (solo si dice algo que el título no: procedencia o tipo de métrica) + título + qué se mide."""
    ov = f'<div class="da-overline">{html.escape(overline)}</div>' if overline else ""
    return f'{ov}<div class="da-h3">{html.escape(title)}</div><div class="da-sub">{html.escape(subtitle)}</div>'


def chart_frame(key: str, overline: str, title: str, subtitle: str, fig: go.Figure, data: pd.DataFrame | None = None,
                source: str | None = "Fuente: Transactions.csv, agregado · corte oct-2024", height: int = 360,
                ysuffix: str | None = None, right: int = 16, month_ticks: bool = True) -> None:
    """ChartFrame: título que enuncia el hallazgo + qué se mide + gráfico + Ver datos + fuente (omitible si es común)."""
    with st.container(border=True, key=f"frame_{key}"):
        st.markdown(_head(overline, title, subtitle), unsafe_allow_html=True)
        st.plotly_chart(style(fig, height, ysuffix, right, month_ticks), width="stretch",
                        config={"displayModeBar": False}, key=f"chart_{key}")
        if data is not None:
            with st.expander("Ver datos"):
                st.dataframe(es_table(data), hide_index=True, width="stretch")
        if source:
            st.markdown(f'<div class="da-source">{html.escape(source)}</div>', unsafe_allow_html=True)


def text_frame(key: str, overline: str, title: str, subtitle: str, df: pd.DataFrame, source: str | None = None) -> None:
    """Tabla de frases (reglas, pasos, hipótesis): HTML que envuelve el texto; para cifras, usar table_frame."""
    head = "".join(f"<th>{html.escape(str(c))}</th>" for c in df.columns)
    rows = "".join("<tr>" + "".join(f"<td>{html.escape(str(v))}</td>" for v in r) + "</tr>"
                   for r in df.itertuples(index=False))
    src = f'<div class="da-source">{html.escape(source)}</div>' if source else ""
    with st.container(border=True, key=f"frame_{key}"):
        st.markdown(_head(overline, title, subtitle) +
                    f'<table class="da-table"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>{src}',
                    unsafe_allow_html=True)


def table_frame(key: str, overline: str, title: str, subtitle: str, df: pd.DataFrame, source: str | None = None) -> None:
    with st.container(border=True, key=f"frame_{key}"):
        st.markdown(_head(overline, title, subtitle), unsafe_allow_html=True)
        st.dataframe(es_table(df), hide_index=True, width="stretch")
        if source:
            st.markdown(f'<div class="da-source">{html.escape(source)}</div>', unsafe_allow_html=True)
