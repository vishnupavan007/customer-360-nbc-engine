"""Shared theme utilities — import on every page."""
import streamlit as st

# ── Dark mode colour tokens ────────────────────────────────────────────────────
_D = dict(
    bg="#0E1117", secondary="#1a1c2e", sidebar="#161824",
    text="#FAFAFA", muted="#9EABB7", border="#2a2d42",
    primary="#29B5E8", card="#1c1e2e",
    input_bg="#1c1e2e", input_fg="#E0E0E0", placeholder="#546E7A",
    btn_bg="#1a1c2e",
)


# ── Shared HTML table renderer (theme-aware) ───────────────────────────────────
def _df_to_html(df, dark=False, col_styles=None):
    """
    Convert a DataFrame to a styled HTML table.
    col_styles: dict of {col_name: callable(value) -> css_string}
    """
    bg        = "#1c2235"  if dark else "#FFFFFF"
    header_bg = "#1a3050"  if dark else "#E3F2FD"
    text_col  = "#CFD8DC"  if dark else "#1A237E"
    muted_col = "#90A4AE"  if dark else "#546E7A"
    border    = "#2a2d42"  if dark else "#CFD8DC"
    alt_bg    = "#161828"  if dark else "#F8FAFC"

    col_styles = col_styles or {}
    cols = df.columns.tolist()

    th = (f"padding:8px 14px;text-align:left;font-size:0.76rem;font-weight:700;"
          f"color:{muted_col};background:{header_bg};border-bottom:2px solid {border};"
          f"white-space:nowrap;letter-spacing:.04em")
    header = "".join(f"<th style='{th}'>{c}</th>" for c in cols)

    rows_html = []
    for idx, (_, row) in enumerate(df.iterrows()):
        row_bg = alt_bg if idx % 2 else bg
        cells = []
        for c in cols:
            val = row[c]
            extra = ""
            if c in col_styles:
                extra = col_styles[c](val)
            td = (f"padding:7px 14px;font-size:0.82rem;color:{text_col};"
                  f"border-bottom:1px solid {border};{extra}")
            cells.append(f"<td style='{td}'>{val}</td>")
        rows_html.append(f"<tr style='background:{row_bg}'>{''.join(cells)}</tr>")

    return (
        f"<div style='overflow-x:auto;margin:8px 0;border-radius:10px;"
        f"border:1px solid {border};overflow:hidden'>"
        f"<table style='width:100%;border-collapse:collapse;background:{bg}'>"
        f"<thead><tr>{header}</tr></thead>"
        f"<tbody>{''.join(rows_html)}</tbody>"
        f"</table></div>"
    )


def render_df(df, col_styles=None):
    """Render a DataFrame as a themed HTML table. Call instead of st.dataframe()."""
    dark = st.session_state.get("dark_mode", False)
    st.markdown(_df_to_html(df, dark=dark, col_styles=col_styles),
                unsafe_allow_html=True)


# ── Dark CSS overrides ─────────────────────────────────────────────────────────
def _dark_css(c):
    bg = c["bg"]; secondary = c["secondary"]; sidebar = c["sidebar"]
    text = c["text"]; muted = c["muted"]; border = c["border"]
    primary = c["primary"]; card = c["card"]
    input_bg = c["input_bg"]; input_fg = c["input_fg"]
    placeholder = c["placeholder"]; btn_bg = c["btn_bg"]

    return f"""<style>
/* ══ DARK MODE OVERRIDES ══════════════════════════════════════════════════ */
body, .stApp {{ background-color:{bg} !important; color:{text} !important; }}
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div,
section[data-testid="stSidebar"] {{
    background-color:{sidebar} !important;
    border-right:1px solid {border} !important;
}}
[data-testid="block-container"] {{ background-color:{bg} !important; }}

p, li, .stMarkdown,
[data-testid="stMarkdownContainer"] p {{ color:{text} !important; }}
h1,h2,h3,h4,h5,h6 {{ color:{text} !important; }}
small, .stCaption p {{ color:{muted} !important; }}

/* ── Sidebar text ── */
[data-testid="stSidebar"] p     {{ color:{muted} !important; }}
[data-testid="stSidebar"] label {{ color:{text}  !important; }}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3    {{ color:{text}  !important; }}

/* ── Sidebar navigation links ── */
[data-testid="stSidebarNav"]         {{ background-color:{sidebar} !important; }}
[data-testid="stSidebarNavLink"]     {{
    color:{text}              !important;
    border-radius:6px         !important;
    padding:6px 10px          !important;
}}
[data-testid="stSidebarNavLink"] p,
[data-testid="stSidebarNavLink"] span {{ color:{text} !important; }}
[data-testid="stSidebarNavLink"]:hover {{
    background-color:{secondary} !important;
}}
[data-testid="stSidebarNavLink"][aria-current="page"],
[data-testid="stSidebarNavLink"][aria-selected="true"] {{
    background-color:{primary}25 !important;
    border-left:3px solid {primary} !important;
}}
[data-testid="stSidebarNavLink"][aria-current="page"] span,
[data-testid="stSidebarNavLink"][aria-current="page"] p {{
    color:{primary} !important; font-weight:700 !important;
}}

/* ── Inputs ── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stSelectbox"] [data-baseweb="select"] > div {{
    background-color:{input_bg} !important;
    color:{input_fg}            !important;
    border-color:{border}       !important;
}}
[data-testid="stTextInput"] input::placeholder,
[data-testid="stTextArea"] textarea::placeholder {{ color:{placeholder} !important; }}

/* ── Buttons ── */
button[kind="secondary"] {{
    background-color:{btn_bg} !important;
    color:{text}              !important;
    border-color:{border}     !important;
}}

/* ── Metric cards ── */
div[data-testid="metric-container"],
div[data-testid="stMetric"] {{
    background-color:{card}   !important;
    border:1px solid {border} !important;
    border-radius:10px        !important;
    padding:14px 16px         !important;
}}
div[data-testid="stMetricLabel"] p {{ color:{muted} !important; font-size:0.82rem !important; }}
div[data-testid="stMetricValue"] > div {{ color:{text} !important; }}

/* ── Expanders / Forms ── */
[data-testid="stExpander"], details summary {{
    background-color:{secondary} !important;
    color:{text}                 !important;
    border:1px solid {border}    !important;
    border-radius:8px            !important;
}}
.streamlit-expanderContent {{ background-color:{secondary} !important; }}
[data-testid="stForm"] {{
    background-color:{secondary} !important;
    border:1px solid {border}    !important;
    border-radius:8px            !important;
    padding:8px                  !important;
}}

/* ── Alerts / Dividers ── */
.stAlert {{ background-color:{secondary} !important; color:{text} !important; }}
hr, [data-testid="stDivider"] {{ border-color:{border} !important; opacity:0.4; }}

/* ── Charts — card-frame the white Altair area ── */
[data-testid="stArrowVegaLiteChart"],
[data-testid="stVegaLiteChart"] {{
    background-color:#FFFFFF  !important;
    border-radius:12px        !important;
    border:1px solid {border} !important;
    padding:12px 8px 4px 8px  !important;
    overflow:hidden           !important;
}}

/* ── Multiselect tags ── */
[data-testid="stMultiSelect"] [data-baseweb="tag"] {{
    background-color:{primary}20 !important;
    color:{primary}              !important;
}}

/* ── Tabs ── */
[data-testid="stTab"] button {{ color:{muted} !important; }}
[data-testid="stTab"] button[aria-selected="true"] {{
    color:{primary} !important;
    border-bottom-color:{primary} !important;
}}

[data-testid="stDecoration"] {{ display:none; }}
footer {{ visibility:hidden; }}
</style>"""


def apply_theme():
    """Inject dark CSS overrides when dark mode is active."""
    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False
    if st.session_state.dark_mode:
        st.markdown(_dark_css(_D), unsafe_allow_html=True)
    else:
        st.markdown("""<style>
[data-testid="stDecoration"] { display:none; }
footer { visibility:hidden; }
</style>""", unsafe_allow_html=True)


def theme_sidebar():
    """Render dark/light toggle inside the sidebar."""
    prev = st.session_state.get("dark_mode", False)
    icon  = "☀️" if prev else "🌙"
    label = f"{icon} {'Light Mode' if prev else 'Dark Mode'}"
    new   = st.toggle(label, value=prev, key="_global_theme")
    if new != prev:
        st.session_state.dark_mode = new
        st.rerun()
