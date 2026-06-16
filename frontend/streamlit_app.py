"""
frontend/streamlit_app.py
--------------------------
Streamlit frontend for the AI Contract Risk Analyzer.
"""

import streamlit as st
import requests
import json
from pathlib import Path

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Contract Risk Analyzer",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

BACKEND_URL = "http://localhost:8000"

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.main { background: #0f1117; }

/* Risk Badges */
.badge-critical { background:#7c0a02; color:#fff; padding:4px 12px; border-radius:20px; font-weight:600; font-size:13px; }
.badge-high     { background:#c0392b; color:#fff; padding:4px 12px; border-radius:20px; font-weight:600; font-size:13px; }
.badge-medium   { background:#e67e22; color:#fff; padding:4px 12px; border-radius:20px; font-weight:600; font-size:13px; }
.badge-low      { background:#27ae60; color:#fff; padding:4px 12px; border-radius:20px; font-weight:600; font-size:13px; }

/* Clause Card */
.clause-card {
    background: #1e2130;
    border: 1px solid #2d3250;
    border-radius: 12px;
    padding: 20px;
    margin: 12px 0;
    transition: border-color 0.2s;
}
.clause-card:hover { border-color: #4f6ef7; }
.clause-card h4    { color: #e2e8f0; margin: 0 0 8px; font-size: 15px; font-weight: 600; }
.clause-card p     { color: #94a3b8; font-size: 13px; line-height: 1.6; margin: 0; }

/* Score Ring */
.score-ring {
    display: flex; align-items: center; justify-content: center;
    width: 90px; height: 90px; border-radius: 50%;
    font-size: 26px; font-weight: 700; color: #fff;
}

/* Summary Box */
.summary-box {
    background: linear-gradient(135deg, #1e2130 0%, #252a3d 100%);
    border: 1px solid #3b4fd8;
    border-radius: 16px;
    padding: 28px;
    margin: 16px 0;
}
.summary-box h3 { color: #7c9ef8; margin-top: 0; font-size: 18px; }
.summary-box p  { color: #cbd5e1; line-height: 1.8; }

/* Missing Clause */
.missing-card {
    background: #1a1208;
    border-left: 4px solid #f59e0b;
    border-radius: 8px;
    padding: 14px 18px;
    margin: 8px 0;
}
.missing-card h5 { color: #fbbf24; margin: 0 0 6px; font-size: 14px; }
.missing-card p  { color: #d1a94a; font-size: 13px; margin: 0; }

/* Metric Cards */
.metric-card {
    background: #1e2130;
    border: 1px solid #2d3250;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
}
.metric-card .metric-val  { font-size: 36px; font-weight: 700; color: #e2e8f0; }
.metric-card .metric-lbl  { font-size: 13px; color: #64748b; margin-top: 4px; }

/* Hero */
.hero {
    background: linear-gradient(135deg, #1e2130 0%, #0f172a 100%);
    border: 1px solid #2d3250;
    border-radius: 20px;
    padding: 40px;
    text-align: center;
    margin-bottom: 30px;
}
.hero h1 { color: #e2e8f0; font-size: 32px; font-weight: 700; margin-bottom: 8px; }
.hero p  { color: #64748b; font-size: 16px; }

/* Step badges */
.step { display:inline-block; background:#3b4fd8; color:#fff;
        width:24px; height:24px; border-radius:50%;
        text-align:center; line-height:24px; font-size:12px;
        font-weight:700; margin-right:8px; }
</style>
""", unsafe_allow_html=True)


# ── Helper Functions ─────────────────────────────────────────────────────────
def get_risk_color(level: str) -> str:
    colors = {"Critical": "#7c0a02", "High": "#c0392b", "Medium": "#e67e22", "Low": "#27ae60"}
    return colors.get(level, "#64748b")

def get_risk_badge(level: str) -> str:
    cls = level.lower() if level.lower() in ["critical","high","medium","low"] else "low"
    return f'<span class="badge-{cls}">{level}</span>'

def get_score_color(score: int) -> str:
    if score >= 81: return "#7c0a02"
    if score >= 61: return "#c0392b"
    if score >= 41: return "#e67e22"
    return "#27ae60"

def upload_file(file_bytes, filename: str) -> dict | None:
    try:
        resp = requests.post(
            f"{BACKEND_URL}/upload/",
            files={"file": (filename, file_bytes, "application/pdf")},
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()
        st.error(f"Upload failed: {resp.json().get('detail', resp.text)}")
        return None
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to backend. Start the FastAPI server first:\n```\npython -m uvicorn app.main:app --reload\n```")
        return None
    except Exception as e:
        st.error(f"Upload error: {e}")
        return None

def analyze_contract(file_id: str, filename: str) -> dict | None:
    try:
        resp = requests.post(
            f"{BACKEND_URL}/analyze/{file_id}",
            params={"original_filename": filename},
            timeout=300,  # AI analysis can take time
        )
        if resp.status_code == 200:
            return resp.json()
        err = resp.json()
        detail = err.get("detail") or err.get("error") or resp.text
        st.error(f"Analysis failed: {detail}")
        return None
    except requests.exceptions.Timeout:
        st.error("Analysis timed out. The contract may be too large.")
        return None
    except Exception as e:
        st.error(f"Analysis error: {e}")
        return None


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚖️ Contract Risk Analyzer")
    st.markdown("---")
    st.markdown("""
**How it works:**

<span class="step">1</span> Upload a PDF contract  
<span class="step">2</span> AI extracts all clauses  
<span class="step">3</span> Each clause is risk-scored  
<span class="step">4</span> Missing clauses detected  
<span class="step">5</span> Executive summary generated  
""", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("**Powered by**")
    st.markdown("🤖 Google Gemini 2.0 Flash  \n📄 PyMuPDF  \n⚡ FastAPI")
    st.markdown("---")
    st.caption("v1.0.0 | For demo & interview purposes")


# ── Main Page ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>⚖️ AI Contract Risk Analyzer</h1>
  <p>Upload any legal contract PDF and get instant AI-powered risk analysis, clause extraction, and executive summary.</p>
</div>
""", unsafe_allow_html=True)

# ── Upload Section ────────────────────────────────────────────────────────────
st.markdown("### 📤 Upload Contract")
uploaded_file = st.file_uploader(
    "Drop your PDF contract here",
    type=["pdf"],
    help="Maximum file size: 10MB. Supported: Service agreements, NDAs, employment contracts, etc.",
)

if uploaded_file:
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.info(f"📄 **{uploaded_file.name}** — {uploaded_file.size / 1024:.1f} KB")
    with col3:
        analyze_btn = st.button("🚀 Analyze Contract", type="primary", use_container_width=True)

    if analyze_btn:
        # Step 1: Upload
        with st.spinner("📤 Uploading contract..."):
            upload_result = upload_file(uploaded_file.getvalue(), uploaded_file.name)

        if upload_result:
            file_id = upload_result["file_id"]
            st.success(f"✅ Uploaded successfully! File ID: `{file_id}`")

            # Step 2: Analyze
            with st.spinner("🤖 AI is analyzing your contract... (this may take 30-60 seconds)"):
                progress = st.progress(0, text="Extracting text from PDF...")
                import time
                for pct, msg in [(20, "Identifying clauses..."), (40, "Analyzing risks..."),
                                  (70, "Detecting missing clauses..."), (90, "Generating summary...")]:
                    time.sleep(0.5)
                    progress.progress(pct, text=msg)

                result = analyze_contract(file_id, uploaded_file.name)
                progress.progress(100, text="Analysis complete!")
                time.sleep(0.3)
                progress.empty()

            if result:
                st.session_state["analysis_result"] = result
                st.session_state["analysis_done"] = True
                st.rerun()


# ── Results Display ───────────────────────────────────────────────────────────
if st.session_state.get("analysis_done") and st.session_state.get("analysis_result"):
    result = st.session_state["analysis_result"]
    summary = result.get("executive_summary", {})

    st.markdown("---")
    st.markdown("## 📊 Analysis Results")

    # ── Top Metrics ──────────────────────────────────────────────────────────
    overall_level = summary.get("overall_risk_level", "Medium")
    overall_score = summary.get("overall_risk_score", 50)

    c1, c2, c3, c4, c5 = st.columns(5)
    metrics = [
        (str(overall_score), "Overall Risk Score", get_score_color(overall_score)),
        (str(result.get("total_clauses_found", 0)), "Clauses Found", "#3b82f6"),
        (str(result.get("high_risk_count", 0)), "High Risk Clauses", "#ef4444"),
        (str(result.get("medium_risk_count", 0)), "Medium Risk", "#f59e0b"),
        (str(result.get("total_missing_clauses", 0)), "Missing Clauses", "#8b5cf6"),
    ]
    for col, (val, label, color) in zip([c1, c2, c3, c4, c5], metrics):
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-val" style="color:{color}">{val}</div>
                <div class="metric-lbl">{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Executive Summary",
        "🔍 Clause Analysis",
        "⚠️ Missing Clauses",
        "📄 Contract Info"
    ])

    # ── Tab 1: Executive Summary ──────────────────────────────────────────────
    with tab1:
        contract_type = summary.get("contract_type", "N/A")
        parties = ", ".join(summary.get("parties_involved", [])) or "N/A"
        risk_badge = get_risk_badge(overall_level)

        st.markdown(f"""
        <div class="summary-box">
            <h3>📝 Executive Summary</h3>
            <p><strong>Contract Type:</strong> {contract_type} &nbsp;|&nbsp;
               <strong>Parties:</strong> {parties} &nbsp;|&nbsp;
               <strong>Risk Level:</strong> {risk_badge}</p>
            <p>{summary.get("summary_text", "No summary available.")}</p>
        </div>""", unsafe_allow_html=True)

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.markdown("#### 📌 Key Obligations")
            for item in summary.get("key_obligations", []):
                st.markdown(f"• {item}")

        with col_b:
            st.markdown("#### ⚠️ Key Risks")
            for item in summary.get("key_risks", []):
                st.markdown(f"• {item}")

        with col_c:
            st.markdown("#### ✅ Recommended Actions")
            for item in summary.get("recommended_actions", []):
                st.markdown(f"• {item}")

        red_flags = summary.get("red_flags", [])
        if red_flags:
            st.markdown("#### 🚩 Red Flags")
            for flag in red_flags:
                st.error(f"🚩 {flag}")

    # ── Tab 2: Clause Analysis ────────────────────────────────────────────────
    with tab2:
        clause_risks = result.get("clause_risks", [])
        if not clause_risks:
            st.info("No clause risks found.")
        else:
            # Filter controls
            col_f1, col_f2 = st.columns([1, 2])
            with col_f1:
                filter_level = st.selectbox(
                    "Filter by Risk Level",
                    ["All", "Critical", "High", "Medium", "Low"]
                )
            with col_f2:
                sort_by = st.radio("Sort by", ["Risk Score (High→Low)", "Clause Type"], horizontal=True)

            filtered = clause_risks
            if filter_level != "All":
                filtered = [r for r in clause_risks if r["risk_level"] == filter_level]

            if sort_by == "Clause Type":
                filtered = sorted(filtered, key=lambda r: r["clause_type"])

            st.markdown(f"Showing **{len(filtered)}** of **{len(clause_risks)}** clauses")

            for risk in filtered:
                level = risk.get("risk_level", "Medium")
                score = risk.get("risk_score", 0)
                color = get_score_color(score)

                with st.expander(
                    f"{get_risk_badge(level)} &nbsp; {risk.get('clause_type', 'Unknown')} — Score: {score}/100",
                    expanded=(level in ["Critical", "High"])
                ):
                    col_l, col_r = st.columns([3, 1])
                    with col_l:
                        st.markdown("**📄 Clause Text:**")
                        st.markdown(
                            f"<div style='background:#0f1117;padding:12px;border-radius:8px;"
                            f"color:#94a3b8;font-size:13px;line-height:1.7;border-left:3px solid {color}'>"
                            f"{risk.get('clause_text', '')[:600]}...</div>",
                            unsafe_allow_html=True
                        )
                    with col_r:
                        st.markdown(
                            f"<div class='score-ring' style='background:{color};margin:auto'>{score}</div>",
                            unsafe_allow_html=True
                        )

                    st.markdown("**⚠️ Risk Reason:**")
                    st.warning(risk.get("risk_reason", ""))

                    st.markdown("**💡 Recommendation:**")
                    st.success(risk.get("recommendation", ""))

                    issues = risk.get("key_issues", [])
                    if issues:
                        st.markdown("**🔎 Key Issues:**")
                        for issue in issues:
                            st.markdown(f"  - {issue}")

    # ── Tab 3: Missing Clauses ────────────────────────────────────────────────
    with tab3:
        missing = result.get("missing_clauses", [])
        if not missing:
            st.success("✅ No critical missing clauses detected!")
        else:
            st.warning(f"⚠️ {len(missing)} standard clause(s) are missing from this contract.")
            for m in missing:
                importance = m.get("importance", "Medium")
                color_map = {"Critical": "#7c0a02", "High": "#c0392b", "Medium": "#92400e", "Low": "#1e3a2f"}
                border_color = color_map.get(importance, "#92400e")

                st.markdown(f"""
                <div class="missing-card" style="border-left-color:{border_color}">
                    <h5>{get_risk_badge(importance)} &nbsp; {m.get('clause_type', 'Unknown')}</h5>
                    <p><strong>Risk:</strong> {m.get('description', '')}</p>
                    <p><strong>Action:</strong> {m.get('recommendation', '')}</p>
                </div>""", unsafe_allow_html=True)

    # ── Tab 4: Contract Info ──────────────────────────────────────────────────
    with tab4:
        st.markdown("#### 📄 Contract Metadata")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.metric("Filename", result.get("filename", "N/A"))
            st.metric("Total Pages", result.get("total_pages", "N/A"))
            st.metric("Word Count", f"{result.get('word_count', 0):,}")
        with col_m2:
            st.metric("Analysis ID", result.get("analysis_id", "N/A"))
            st.metric("Clauses Extracted", result.get("total_clauses_found", 0))
            st.metric("Analyzed At", result.get("analyzed_at", "N/A")[:19])

        st.markdown("#### 📥 Download Results")
        json_str = json.dumps(result, indent=2, default=str)
        st.download_button(
            label="⬇️ Download Full Analysis (JSON)",
            data=json_str,
            file_name=f"analysis_{result.get('analysis_id', 'result')}.json",
            mime="application/json",
        )

    # Reset button
    st.markdown("---")
    if st.button("🔄 Analyze Another Contract"):
        st.session_state.clear()
        st.rerun()

else:
    # Empty state
    if not uploaded_file:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;color:#334155">
            <div style="font-size:64px">📄</div>
            <h3 style="color:#475569;margin-top:16px">Upload a Contract to Get Started</h3>
            <p style="color:#64748b">Supported: Service Agreements · NDAs · Employment Contracts · Vendor Agreements</p>
        </div>
        """, unsafe_allow_html=True)
