import streamlit as st
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import datetime
import io
import base64

# ── Page config ───────────────────────────────────────────────
st.set_page_config(page_title="Stock Gain Finder", page_icon="📈", layout="centered")

st.markdown("""
<style>
  .stApp { background-color: #0f172a; color: #f1f5f9; }
  .block-container { max-width: 780px; padding-top: 2rem; }
  .card {
    background: #1e293b; border: 1px solid #334155; border-radius: 10px;
    padding: 14px 16px; margin-bottom: 4px;
  }
  .card-label { font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }
  .card-val { font-size: 22px; font-weight: 700; }
  .card-sub { font-size: 11px; color: #94a3b8; margin-top: 3px; }
  .citation-box {
    background: #1e293b; border: 1px solid #334155; border-radius: 10px;
    padding: 16px; margin-top: 12px;
  }
</style>
""", unsafe_allow_html=True)

# ── Initialise session state ──────────────────────────────────
if "selected_ticker" not in st.session_state:
    st.session_state.selected_ticker = ""
if "selected_name" not in st.session_state:
    st.session_state.selected_name = ""
if "search_results" not in st.session_state:
    st.session_state.search_results = []
if "search_query" not in st.session_state:
    st.session_state.search_query = ""

# ── Ticker search ─────────────────────────────────────────────
def get_suggestions(query):
    if not query:
        return []
    try:
        results = yf.Search(query, max_results=8).quotes or []
        out = []
        for r in results:
            if r.get("quoteType") in ("EQUITY", "ETF"):
                name = r.get("longname") or r.get("shortname") or ""
                out.append({
                    "ticker": r.get("symbol", ""),
                    "name": name,
                    "exchange": r.get("exchDisp") or r.get("exchange") or ""
                })
        return out
    except:
        return []

# ── Header ────────────────────────────────────────────────────
st.markdown("<h1 style='color:#10b981;margin-bottom:4px'>📈 Stock Gain Finder</h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#94a3b8;margin-bottom:24px'>Find the peak gain for any stock between two dates.</p>", unsafe_allow_html=True)

# ── Step 1: Stock search ──────────────────────────────────────
st.markdown("<p style='color:#94a3b8;font-size:13px;font-weight:600;margin-bottom:6px'>STEP 1 — FIND YOUR STOCK</p>", unsafe_allow_html=True)

col_input, col_btn = st.columns([4, 1])
with col_input:
    search_query = st.text_input("", placeholder="Type company name or ticker e.g. Apple, TSLA...",
                                  label_visibility="collapsed", key="search_input")
with col_btn:
    search_clicked = st.button("Search", use_container_width=True)

# Run search and store results in session state
if search_clicked and search_query:
    with st.spinner("Searching..."):
        st.session_state.search_results = get_suggestions(search_query)
        st.session_state.search_query = search_query
        # Clear previous selection when doing a new search
        st.session_state.selected_ticker = ""
        st.session_state.selected_name = ""

# Show search results as buttons — stored in session state so they persist
if st.session_state.search_results and not st.session_state.selected_ticker:
    st.markdown("<p style='color:#94a3b8;font-size:13px;margin-bottom:4px'>Select a stock:</p>", unsafe_allow_html=True)
    for m in st.session_state.search_results:
        label = f"{m['ticker']}  —  {m['name']}  ({m['exchange']})"
        if st.button(label, key=f"pick_{m['ticker']}"):
            st.session_state.selected_ticker = m["ticker"]
            st.session_state.selected_name = m["name"]
            st.session_state.search_results = []  # hide results once selected
            st.rerun()

# Show currently selected stock
if st.session_state.selected_ticker:
    st.markdown(
        f"<div style='color:#10b981;font-weight:700;font-size:15px;margin:8px 0'>"
        f"✅ Selected: {st.session_state.selected_ticker} "
        f"<span style='color:#94a3b8;font-weight:400;font-size:13px'>— {st.session_state.selected_name}</span>"
        f"</div>",
        unsafe_allow_html=True
    )
    if st.button("✕ Change stock", key="clear_ticker"):
        st.session_state.selected_ticker = ""
        st.session_state.selected_name = ""
        st.session_state.search_results = []
        st.rerun()

# ── Step 2: Date range ────────────────────────────────────────
st.markdown("<p style='color:#94a3b8;font-size:13px;font-weight:600;margin-top:20px;margin-bottom:6px'>STEP 2 — PICK YOUR DATE RANGE</p>", unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Start Date", value=None,
                                min_value=datetime.date(1980, 1, 1),
                                max_value=datetime.date.today())
with col2:
    end_date = st.date_input("End Date", value=None,
                              min_value=datetime.date(1980, 1, 1),
                              max_value=datetime.date.today())

# ── Step 3: Run ───────────────────────────────────────────────
st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)
run_clicked = st.button("Find Peak Gain", use_container_width=False)

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

                    # ── Cards ──────────────────────────────────
                    c1, c2, c3, c4, c5 = st.columns(5)
                    for col, label, val, sub, color in [
                        (c1, "Start Price",    f"${start_price:,.2f}", start_date_str, "#f1f5f9"),
                        (c2, "Peak High",      f"${high_price:,.2f}",  high_date_str,  "#f59e0b"),
                        (c3, "% Gain",         f"+{pct_gain:.2f}%",    "",             "#10b981"),
                        (c4, "Multiple",       f"{multiple:.2f}x",     "",             "#f1f5f9"),
                        (c5, "$1,000 Becomes", f"${final_value:,.2f}", "",             "#10b981"),
                    ]:
                        with col:
                            st.markdown(
                                f"<div class='card'>"
                                f"<div class='card-label'>{label}</div>"
                                f"<div class='card-val' style='color:{color}'>{val}</div>"
                                f"<div class='card-sub'>{sub}</div>"
                                f"</div>",
                                unsafe_allow_html=True
                            )

                    st.markdown(
                        f"<div style='color:#94a3b8;font-size:12px;margin:8px 0'>"
                        f"Source: <a href='{source_url}' target='_blank' style='color:#60a5fa'>{source_url}</a></div>",
                        unsafe_allow_html=True
                    )

                    # ── Chart ──────────────────────────────────
                    fig, ax = plt.subplots(figsize=(11, 4))
                    fig.patch.set_facecolor("#0f172a")
                    ax.set_facecolor("#0f172a")

                    color = "#10b981" if end_price >= start_price else "#ef4444"
                    ax.plot(dates, closes.values, color=color, linewidth=1.8, zorder=3)
                    ax.fill_between(dates, closes.values, float(closes.min()) * 0.97,
                                    alpha=0.15, color=color, zorder=2)

                    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
                    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
                    fig.autofmt_xdate(rotation=30, ha="right")
                    for spine in ax.spines.values():
                        spine.set_edgecolor("#1e293b")
                    ax.tick_params(colors="#64748b", labelsize=9)
                    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.2f}"))
                    ax.grid(axis="y", color="#1e293b", linewidth=0.8, zorder=1)
                    plt.tight_layout()

                    st.pyplot(fig)

                    # ── Download button ────────────────────────
                    buf = io.BytesIO()
                    fig.savefig(buf, format="png", dpi=150, facecolor="#0f172a", bbox_inches="tight")
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
                        f"<div style='color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px'>"
                        f"\U0001f4cb Citation — select all and copy</div>"
                        f"<pre style='color:#cbd5e1;font-size:13px;white-space:pre-wrap;font-family:monospace'>{citation}</pre>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                    st.markdown("<p style='color:#475569;font-size:11px;text-align:center;margin-top:8px'>Always verify figures independently for legal use.</p>", unsafe_allow_html=True)

            except Exception as e:
                st.error(f"Error: {e}")
