import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import datetime
import io
from difflib import SequenceMatcher

# ── Page config ───────────────────────────────────────────────
st.set_page_config(page_title="Stock Gain Finder", page_icon="📈", layout="centered")

# ── Theme definitions ─────────────────────────────────────────
THEMES = {
    "dark": {
        "bg":          "#0f172a",
        "bg2":         "#1e293b",
        "border":      "#334155",
        "text":        "#f1f5f9",
        "text2":       "#94a3b8",
        "text3":       "#64748b",
        "accent":      "#10b981",
        "amber":       "#f59e0b",
        "link":        "#60a5fa",
        "chart_bg":    "#0f172a",
        "chart_grid":  "#1e293b",
        "chart_tick":  "#64748b",
        "dl_btn":      "#1e40af",
        "dl_btn_hover":"#1d4ed8",
        "toggle_label":"☀️ Light mode",
    },
    "light": {
        "bg":          "#f8fafc",
        "bg2":         "#ffffff",
        "border":      "#e2e8f0",
        "text":        "#0f172a",
        "text2":       "#475569",
        "text3":       "#94a3b8",
        "accent":      "#059669",
        "amber":       "#d97706",
        "link":        "#2563eb",
        "chart_bg":    "#ffffff",
        "chart_grid":  "#f1f5f9",
        "chart_tick":  "#94a3b8",
        "dl_btn":      "#2563eb",
        "dl_btn_hover":"#1d4ed8",
        "toggle_label":"🌙 Dark mode",
    }
}

# ── Initialise session state ──────────────────────────────────
for key, val in [("selected_ticker", ""), ("selected_name", ""),
                 ("search_results", []), ("search_query", ""),
                 ("theme", "dark")]:
    if key not in st.session_state:
        st.session_state[key] = val

t = THEMES[st.session_state.theme]

# ── Inject CSS based on current theme ────────────────────────
st.markdown(f"""
<style>
  html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"],
  .stApp, section.main, .main .block-container {{
    background-color: {t['bg']} !important;
    color: {t['text']} !important;
  }}
  [data-testid="stHeader"] {{
    background-color: {t['bg']} !important;
    border-bottom: 1px solid {t['border']} !important;
  }}
  p, span, label, div {{ color: {t['text']} !important; }}
  input, textarea, [data-baseweb="input"] input {{
    background-color: {t['bg2']} !important;
    color: {t['text']} !important;
    border: 1px solid {t['border']} !important;
    border-radius: 8px !important;
  }}
  .stButton > button {{
    background-color: {t['bg2']} !important;
    color: {t['text']} !important;
    border: 1px solid {t['border']} !important;
    border-radius: 8px !important;
    font-size: 14px !important;
  }}
  .stButton > button:hover {{
    background-color: {t['border']} !important;
    border-color: {t['accent']} !important;
    color: {t['accent']} !important;
  }}
  [data-testid="stDateInput"] input {{
    background-color: {t['bg2']} !important;
    color: {t['text']} !important;
    border: 1px solid {t['border']} !important;
  }}
  .stDownloadButton > button {{
    background-color: {t['dl_btn']} !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
  }}
  .stDownloadButton > button:hover {{ background-color: {t['dl_btn_hover']} !important; }}
  .stAlert {{ background-color: {t['bg2']} !important; }}
  .block-container {{ max-width: 780px; padding-top: 2rem; }}
  .card {{
    background: {t['bg2']}; border: 1px solid {t['border']}; border-radius: 10px;
    padding: 14px 16px; margin-bottom: 4px;
  }}
  .card-label {{ font-size: 11px; color: {t['text3']} !important; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }}
  .card-val {{ font-size: 22px; font-weight: 700; }}
  .card-sub {{ font-size: 11px; color: {t['text2']} !important; margin-top: 3px; }}
  .citation-box {{
    background: {t['bg2']}; border: 1px solid {t['border']}; border-radius: 10px;
    padding: 16px; margin-top: 12px;
  }}
</style>
""", unsafe_allow_html=True)

# ── Fuzzy search ──────────────────────────────────────────────
def fuzzy_score(query, name, ticker):
    q = query.lower().strip()
    name_score   = SequenceMatcher(None, q, name.lower()).ratio()
    ticker_score = SequenceMatcher(None, q, ticker.lower()).ratio()
    starts_bonus  = 0.3  if name.lower().startswith(q) else 0
    contains_bonus = 0.15 if q in name.lower() else 0
    return max(name_score, ticker_score) + starts_bonus + contains_bonus

def get_suggestions(query):
    if not query:
        return []
    try:
        queries_to_try = [query]
        if len(query) > 3:
            queries_to_try.append(query[:-1])
        if " " in query:
            queries_to_try.append(query.split()[0])
        seen, all_results = set(), []
        for q in queries_to_try:
            try:
                for r in (yf.Search(q, max_results=8).quotes or []):
                    ticker = r.get("symbol", "")
                    if r.get("quoteType") in ("EQUITY", "ETF") and ticker not in seen:
                        seen.add(ticker)
                        name = r.get("longname") or r.get("shortname") or ""
                        all_results.append({
                            "ticker": ticker, "name": name,
                            "exchange": r.get("exchDisp") or r.get("exchange") or "",
                            "score": fuzzy_score(query, name, ticker)
                        })
            except:
                continue
        all_results.sort(key=lambda x: x["score"], reverse=True)
        return all_results[:8]
    except:
        return []

# ── Header row with toggle ────────────────────────────────────
h_col, toggle_col = st.columns([5, 1])
with h_col:
    st.markdown(f"<h1 style='color:{t['accent']};margin-bottom:4px'>📈 Stock Gain Finder</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:{t['text2']};margin-bottom:24px'>Find the peak gain for any stock between two dates.</p>", unsafe_allow_html=True)
with toggle_col:
    st.markdown("<div style='margin-top:18px'></div>", unsafe_allow_html=True)
    if st.button(t["toggle_label"], key="theme_toggle"):
        st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
        st.rerun()

# ── Step 1: Stock search ──────────────────────────────────────
st.markdown(f"<p style='color:{t['text2']};font-size:13px;font-weight:600;margin-bottom:6px'>STEP 1 — FIND YOUR STOCK</p>", unsafe_allow_html=True)

col_input, col_btn = st.columns([4, 1])
with col_input:
    search_query = st.text_input("", placeholder="Type company name or ticker e.g. Apple, TSLA...",
                                  label_visibility="collapsed", key="search_input")
with col_btn:
    search_clicked = st.button("Search", use_container_width=True)

if search_clicked and search_query:
    with st.spinner("Searching..."):
        st.session_state.search_results = get_suggestions(search_query)
        st.session_state.search_query   = search_query
        st.session_state.selected_ticker = ""
        st.session_state.selected_name   = ""
    if not st.session_state.search_results:
        st.warning(f"No results found for '{search_query}'. Try a different spelling.")

if st.session_state.search_results and not st.session_state.selected_ticker:
    st.markdown(f"<p style='color:{t['text2']};font-size:13px;margin-bottom:4px'>Select a stock:</p>", unsafe_allow_html=True)
    for m in st.session_state.search_results:
        label = f"{m['ticker']}  —  {m['name']}  ({m['exchange']})"
        if st.button(label, key=f"pick_{m['ticker']}"):
            st.session_state.selected_ticker = m["ticker"]
            st.session_state.selected_name   = m["name"]
            st.session_state.search_results  = []
            st.rerun()

if st.session_state.selected_ticker:
    st.markdown(
        f"<div style='color:{t['accent']};font-weight:700;font-size:15px;margin:8px 0'>"
        f"✅ Selected: {st.session_state.selected_ticker} "
        f"<span style='color:{t['text2']};font-weight:400;font-size:13px'>— {st.session_state.selected_name}</span>"
        f"</div>", unsafe_allow_html=True
    )
    if st.button("✕ Change stock", key="clear_ticker"):
        st.session_state.selected_ticker = ""
        st.session_state.selected_name   = ""
        st.session_state.search_results  = []
        st.rerun()

# ── Step 2: Date range ────────────────────────────────────────
st.markdown(f"<p style='color:{t['text2']};font-size:13px;font-weight:600;margin-top:20px;margin-bottom:6px'>STEP 2 — PICK YOUR DATE RANGE</p>", unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    start_str = st.text_input("Start Date", placeholder="DD/MM/YYYY", label_visibility="visible")
with col2:
    end_str = st.text_input("End Date", placeholder="DD/MM/YYYY", label_visibility="visible")

# Parse typed dates
def parse_date(s):
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return datetime.datetime.strptime(s.strip(), fmt).date()
        except:
            continue
    return None

start_date = parse_date(start_str) if start_str else None
end_date   = parse_date(end_str)   if end_str   else None

if start_str and not start_date:
    st.warning("Start date format not recognised — please use DD/MM/YYYY e.g. 03/01/2020")
if end_str and not end_date:
    st.warning("End date format not recognised — please use DD/MM/YYYY e.g. 12/03/2026")

st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)
run_clicked = st.button("🔍 Find Peak Gain", type="primary")

if run_clicked:
    sym = st.session_state.selected_ticker.strip().upper()
    if not sym:
        st.error("Please search for and select a stock first.")
    elif not start_date or not end_date:
        st.error("Please select both a start and end date.")
    elif end_date <= start_date:
        st.error("End date must be after start date.")
    else:
        with st.spinner(f"Fetching data for {sym}..."):
            try:
                end_fetch = end_date + datetime.timedelta(days=1)
                df = yf.download(sym, start=str(start_date), end=str(end_fetch),
                                 progress=False, auto_adjust=True)

                if df.empty:
                    st.error(f"No data found for {sym}. Check the ticker and date range.")
                else:
                    closes      = df["Close"].squeeze()
                    dates       = closes.index
                    start_price = float(closes.iloc[0])
                    high_price  = float(closes.max())
                    high_idx    = closes.idxmax()
                    end_price   = float(closes.iloc[-1])

                    start_date_str = dates[0].strftime("%d %B %Y")
                    high_date_str  = high_idx.strftime("%d %B %Y")
                    end_date_str   = end_date.strftime("%d %B %Y")

                    pct_gain    = (high_price - start_price) / start_price * 100
                    multiple    = high_price / start_price
                    final_value = 1000 * multiple
                    source_url  = f"https://finance.yahoo.com/quote/{sym}/history/"

                    st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)

                    # ── Cards ──────────────────────────────────
                    c1, c2, c3, c4, c5 = st.columns(5)
                    for col, label, val, sub, color in [
                        (c1, "Start Price",    f"${start_price:,.2f}", start_date_str, t['text']),
                        (c2, "Peak High",      f"${high_price:,.2f}",  high_date_str,  t['amber']),
                        (c3, "% Gain",         f"+{pct_gain:.2f}%",    "",             t['accent']),
                        (c4, "Multiple",       f"{multiple:.2f}x",     "",             t['text']),
                        (c5, "$1,000 Becomes", f"${final_value:,.2f}", "",             t['accent']),
                    ]:
                        with col:
                            st.markdown(
                                f"<div class='card'>"
                                f"<div class='card-label'>{label}</div>"
                                f"<div class='card-val' style='color:{color}'>{val}</div>"
                                f"<div class='card-sub'>{sub}</div>"
                                f"</div>", unsafe_allow_html=True
                            )

                    st.markdown(
                        f"<div style='color:{t['text2']};font-size:12px;margin:12px 0'>"
                        f"Source: <a href='{source_url}' target='_blank' style='color:{t['link']}'>{source_url}</a></div>",
                        unsafe_allow_html=True
                    )

                    # ── Chart ──────────────────────────────────
                    fig, ax = plt.subplots(figsize=(11, 4))
                    fig.patch.set_facecolor(t['chart_bg'])
                    ax.set_facecolor(t['chart_bg'])

                    line_color = "#10b981" if end_price >= start_price else "#ef4444"
                    ax.plot(dates, closes.values, color=line_color, linewidth=1.8, zorder=3)
                    ax.fill_between(dates, closes.values, float(closes.min()) * 0.97,
                                    alpha=0.15, color=line_color, zorder=2)

                    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
                    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
                    fig.autofmt_xdate(rotation=30, ha="right")
                    for spine in ax.spines.values():
                        spine.set_edgecolor(t['border'])
                    ax.tick_params(colors=t['chart_tick'], labelsize=9)
                    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.2f}"))
                    ax.grid(axis="y", color=t['chart_grid'], linewidth=0.8, zorder=1)
                    plt.tight_layout()
                    st.pyplot(fig)

                    # ── Download button ────────────────────────
                    buf = io.BytesIO()
                    fig.savefig(buf, format="png", dpi=150, facecolor=t['chart_bg'], bbox_inches="tight")
                    buf.seek(0)
                    plt.close(fig)
                    st.download_button(
                        label="⬇ Download Chart Image",
                        data=buf,
                        file_name=f"{sym}_chart.png",
                        mime="image/png"
                    )

                    # ── Citation ───────────────────────────────
                    citation = (
                        f"{sym} — Stock Gain Analysis\n"
                        f"Source: {source_url}\n"
                        f"Start:     {start_date_str} @ ${start_price:,.2f}\n"
                        f"Peak High: {high_date_str} @ ${high_price:,.2f}\n"
                        f"Gain: +{pct_gain:.2f}% | {multiple:.2f}x multiple | $1,000 \u2192 ${final_value:,.2f}"
                    )
                    st.markdown(
                        f"<div class='citation-box'>"
                        f"<div style='color:{t['text3']};font-size:11px;text-transform:uppercase;"
                        f"letter-spacing:1px;margin-bottom:8px'>\U0001f4cb Citation — select all and copy</div>"
                        f"<pre style='color:{t['text']};font-size:13px;white-space:pre-wrap;"
                        f"font-family:monospace'>{citation}</pre>"
                        f"</div>", unsafe_allow_html=True
                    )
                    st.markdown(
                        f"<p style='color:{t['text3']};font-size:11px;text-align:center;margin-top:8px'>"
                        f"Always verify figures independently for legal use.</p>",
                        unsafe_allow_html=True
                    )

            except Exception as e:
                st.error(f"Error: {e}")
