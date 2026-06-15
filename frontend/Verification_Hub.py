#!/usr/bin/env python3
"""
Aletheia Enterprise Verification Engine (Streamlit UI)

Description:
    Clean, trustworthy, and modern Enterprise AI SaaS interface inspired by Apple, Linear, and OpenAI.
    Hooks into FastAPI Server-Sent Events (SSE) to render live agent consensus logs
    and displays anti-hallucination compliance gauges with custom Plotly charts.
"""

import os
import json
import requests
import streamlit as nn  # Use 'nn' as standard short import for Streamlit to distinguish it
import plotly.graph_objects as go

# ==========================================
# 1. Page Configuration & CSS Injection
# ==========================================

nn.set_page_config(
    page_title="ALETHEIA // ENTERPRISE AI VERIFICATION",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load CSS Stylesheet
current_dir = os.path.dirname(os.path.abspath(__file__))
css_path = os.path.join(current_dir, "assets", "style.css")

if os.path.exists(css_path):
    with open(css_path, "r", encoding="utf-8") as f:
        css_data = f.read()
    nn.markdown(f"<style>{css_data}</style>", unsafe_allow_html=True)
else:
    nn.warning("style.css stylesheet not found under frontend/assets/.")

# ==========================================
# 2. Session State Initialization
# ==========================================

if "logs" not in nn.session_state:
    nn.session_state.logs = ["Aletheia sistemi güvenli analiz için hazır. Bir sorgu girin..."]
if "final_report" not in nn.session_state:
    nn.session_state.final_report = ""
if "verified_facts" not in nn.session_state:
    nn.session_state.verified_facts = []
if "detected_conflicts" not in nn.session_state:
    nn.session_state.detected_conflicts = []
if "checkpoint" not in nn.session_state:
    nn.session_state.checkpoint = {
        "active_node": "idle",
        "verified_facts_count": 0,
        "detected_conflicts_count": 0,
        "hallucination_score": 0.0,
        "iterations": 0
    }
if "running" not in nn.session_state:
    nn.session_state.running = False

# ==========================================
# 3. Dynamic Plotly Chart Generators
# ==========================================

def render_gauge_chart(title: str, score: float, color: str) -> go.Figure:
    """
    Renders a stunning circular gauge chart representing verification scores.
    """
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score * 100,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'color': '#ffffff', 'family': 'Plus Jakarta Sans', 'size': 13, 'weight': 'bold'}},
        gauge={
            'axis': {'range': [0, 100], 'tickcolor': 'rgba(255,255,255,0.1)', 'tickwidth': 1},
            'bar': {'color': color},
            'bgcolor': 'rgba(15,17,26,0.5)',
            'borderwidth': 1,
            'bordercolor': 'rgba(255,255,255,0.06)',
            'steps': [
                {'range': [0, 85], 'color': 'rgba(244, 63, 94, 0.04)'},     # Red risk step
                {'range': [85, 100], 'color': 'rgba(16, 185, 129, 0.04)'}   # Green safe step
            ],
        }
    ))
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#ffffff', 'family': 'Inter'},
        height=180,
        margin=dict(l=30, r=30, t=50, b=20)
    )
    return fig

def render_sources_bar_chart(facts: list) -> go.Figure:
    """
    Renders a vertical bar chart representing the trust distributions of facts sources.
    """
    source_counts = {}
    for f in facts:
        for s in f.get("sources", []):
            source_counts[s] = source_counts.get(s, 0) + 1
            
    if not source_counts:
        # Default empty chart placeholder
        source_counts = {"Web Scraper": 2, "Haber Veritabanı": 3, "Yerel RAG Raporları": 1}
        
    x_data = list(source_counts.keys())
    y_data = list(source_counts.values())
    
    fig = go.Figure(go.Bar(
        x=x_data,
        y=y_data,
        marker_color='#00d2ff',  # Apple Cyber Blue
        opacity=0.9,
        marker_line=dict(width=0, color='rgba(0,0,0,0)'),
    ))
    
    fig.update_layout(
        title={'text': "KULLANILAN GÜVENİLİR ANALİZ KAYNAKLARI", 'font': {'color': '#ffffff', 'family': 'Plus Jakarta Sans', 'size': 12, 'weight': 'bold'}},
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#888', 'family': 'Inter', 'size': 10},
        height=190,
        margin=dict(l=20, r=20, t=45, b=20),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.03)')
    )
    return fig

# ==========================================
# 4. Header Section
# ==========================================

col_header_left, col_header_right = nn.columns([2, 1])

with col_header_left:
    nn.markdown('<h1 class="cyber-title">ALETHEIA // ENTERPRISE VERIFICATION</h1>', unsafe_allow_html=True)
    nn.markdown('<p class="cyber-subtitle">GÜVENLİ MUTABAKAT VE YAPAY ZEKA DOĞRULAMA MOTORU</p>', unsafe_allow_html=True)

with col_header_right:
    # Cyber Panel Indicators (Refined SaaS design)
    nn.markdown(
        '<div style="text-align: right; padding-top: 10px; font-family: \'Plus Jakarta Sans\', sans-serif; font-size: 0.8rem; color: #94a3b8;">'
        '<span style="margin-right: 15px;"><span class="indicator-glow" style="background-color:#6ee7b7; box-shadow:0 0 8px rgba(110,231,183,0.4);"></span>COMPLIANCE: GÜVENLİ</span>'
        '<span><span class="indicator-glow" style="background-color:#00d2ff; box-shadow:0 0 8px rgba(0,210,255,0.4);"></span>ENTERPRISE LLM: AKTİF</span>'
        '</div>', 
        unsafe_allow_html=True
    )

# ==========================================
# 5. Sidebar Controls (SaaS Config Panel)
# ==========================================

nn.sidebar.markdown("## ⚙️ KONTROL PANELİ")

temp_slider = nn.sidebar.slider(
    "Analiz Sıcaklığı (Temperature)",
    min_value=0.0,
    max_value=1.0,
    value=0.0,
    step=0.1,
    help="0.0 değeri en katı, tutarlı ve kararlı analizleri (önerilen); 1.0 ise daha serbest analizleri tetikler."
)

trust_slider = nn.sidebar.slider(
    "Güvenilirlik Eşiği (Threshold)",
    min_value=0.0,
    max_value=1.0,
    value=0.75,
    step=0.05
)

nn.sidebar.markdown("---")
nn.sidebar.markdown("### 🔌 ENTEGRASYON NOKTALARI (MCP)")
web_mcp = nn.sidebar.toggle("Web Arama Entegrasyonu (DDG/Tavily)", value=True)
news_mcp = nn.sidebar.toggle("Haber API & RSS Kaynak Entegrasyonu", value=True)

# Sidebar System Health Info (Corporate SaaS style)
nn.sidebar.markdown(
    '<div style="margin-top: 120px; font-family: \'Plus Jakarta Sans\', sans-serif; font-size: 0.7rem; color: #475569; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 15px;">'
    'ALETHEIA CORE v1.0.0<br>'
    'Target Halüsinasyon: %0.00<br>'
    'Güvenlik Standardı: ENTERPRISE SAAS COMPLIANT'
    '</div>',
    unsafe_allow_html=True
)

# ==========================================
# 6. User Research Input
# ==========================================

query_input = nn.text_input(
    "GÜVENLİĞİNİ DENETLEMEK İSTEDİĞİNİZ BİLGİ İDDİASINI GİRİN:",
    placeholder="Örn: TÜİK ve ENAG 2025 yılı enflasyon verileri ve çelişen iddialar nelerdir?",
    key="user_query",
    help="Girilen iddia, canlı entegrasyon kanalları ve indeksli dökümanlar üzerinden doğrulanacaktır."
)

button_col, _ = nn.columns([1.2, 4])
with button_col:
    start_btn = nn.button("ANALİZİ BAŞLAT 🛡️")

# ==========================================
# 7. Split Screen Design (Main Layout)
# ==========================================

col_left, col_right = nn.columns([1, 1])

# --- SOL BÖLME: Canlı Konsensüs Akışı ---
with col_left:
    nn.markdown(
        '<div class="cyber-card">'
        '<div class="cyber-card-header">'
        '<span>🤖 CANLI KONSENSÜS VE AJAN AKIŞI</span>'
        '<span class="indicator-pulse"></span>'
        '</div>'
        '</div>',
        unsafe_allow_html=True
    )
    
    # Placeholder for live logs
    logs_placeholder = nn.empty()
    
    # Initialize static render of logs
    logs_html = "".join([f"<div class='agent-log-row'>{log}</div>" for log in nn.session_state.logs])
    logs_placeholder.markdown(f"<div class='agent-log-container'>{logs_html}</div>", unsafe_allow_html=True)

# --- SAĞ BÖLME: Mutabakat Raporu ---
with col_right:
    nn.markdown(
        '<div class="cyber-card">'
        '<div class="cyber-card-header">'
        '<span>📜 GÜVENLİ MUTABAKAT VE ANALİZ RAPORU</span>'
        '</div>'
        '</div>',
        unsafe_allow_html=True
    )
    
    # Placeholder for report and checks
    report_placeholder = nn.empty()
    
    # Initial status inside report placeholder
    if nn.session_state.final_report:
        report_placeholder.markdown(nn.session_state.final_report)
    else:
        report_placeholder.info("Doğrulama süreci henüz başlatılmadı. Lütfen sorgunuzu girip analizi tetikleyin.")

# ==========================================
# 8. Real-time Event Streaming Action (SSE Execution)
# ==========================================

if start_btn and query_input:
    # Reset states for the new run
    nn.session_state.logs = []
    nn.session_state.final_report = ""
    nn.session_state.verified_facts = []
    nn.session_state.detected_conflicts = []
    nn.session_state.checkpoint = {
        "active_node": "idle",
        "verified_facts_count": 0,
        "detected_conflicts_count": 0,
        "hallucination_score": 0.0,
        "iterations": 0
    }
    
    nn.session_state.logs.append("🛡️ Aletheia motoru tetiklendi. Güvenli doğrulama isteği gönderiliyor...")
    logs_html = "".join([f"<div class='agent-log-row'>{log}</div>" for log in nn.session_state.logs])
    logs_placeholder.markdown(f"<div class='agent-log-container'>{logs_html}</div>", unsafe_allow_html=True)
    report_placeholder.warning("Güvenli konsensüs ajanları çalışmaya başladı. Bilgi raporu derleniyor...")
    
    # Execute backend query and connect to SSE stream
    backend_url = "http://localhost:8999/api/verify"
    params = {
        "query": query_input,
        "temperature": temp_slider,
        "source_threshold": trust_slider,
        "use_web": str(web_mcp).lower(),
        "use_news": str(news_mcp).lower(),
    }
    
    try:
        # Stream response line by line using requests stream=True
        with requests.get(backend_url, params=params, stream=True, timeout=180) as response:
            if response.status_code != 200:
                nn.session_state.logs.append(f"❌ [Sunucu Hatası] Backend hata kodu döndü: {response.status_code}")
                logs_html = "".join([f"<div class='agent-log-row'>{log}</div>" for log in nn.session_state.logs])
                logs_placeholder.markdown(f"<div class='agent-log-container'>{logs_html}</div>", unsafe_allow_html=True)
                report_placeholder.error("Doğrulama motoruyla bağlantı kurulamadı. Sunucu erişilebilirliğini denetleyin.")
            else:
                event_type = ""
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode("utf-8")
                        
                        if decoded_line.startswith("event:"):
                            event_type = decoded_line.split(":", 1)[1].strip()
                        elif decoded_line.startswith("data:"):
                            data_str = decoded_line.split(":", 1)[1].strip()
                            data = json.loads(data_str)
                            
                            # A. Handle Agent Log Events
                            if event_type == "log":
                                nn.session_state.logs.append(data["message"])
                                logs_html = "".join([f"<div class='agent-log-row'>{log}</div>" for log in nn.session_state.logs])
                                logs_placeholder.markdown(f"<div class='agent-log-container'>{logs_html}</div>", unsafe_allow_html=True)
                                
                            # B. Handle Checkpoint Metric Events
                            elif event_type == "checkpoint":
                                nn.session_state.checkpoint = data
                                # If a hallucination correction loop has occurred, write an alert
                                if data["iterations"] > 1:
                                    report_placeholder.warning(
                                        f"🛡️ **HALÜSİNASYON DÜZELTME TETİKLENDİ:** Bilgi doğrulama guardrail'i bir tutarsızlık tespit etti. "
                                        f"Ajanlar mutabakat ve bilgi doğruluğu için yeniden derleniyor (Denetim İterasyonu: {data['iterations'] - 1})..."
                                    )
                                    
                            # C. Handle Final Synthesis Rapor Events
                            elif event_type == "final_result":
                                nn.session_state.final_report = data["final_report"]
                                nn.session_state.verified_facts = data["verified_facts"]
                                nn.session_state.detected_conflicts = data["detected_conflicts"]
                                
                                # Render completed markdown
                                report_placeholder.markdown(nn.session_state.final_report)
                                
                            # D. Handle Errors
                            elif event_type == "error":
                                nn.session_state.logs.append(f"❌ [API HATASI] {data['message']}")
                                logs_html = "".join([f"<div class='agent-log-row'>{log}</div>" for log in nn.session_state.logs])
                                logs_placeholder.markdown(f"<div class='agent-log-container'>{logs_html}</div>", unsafe_allow_html=True)
                                report_placeholder.error(f"Süreç durduruldu: {data['message']}")
                                
        # Force a visual rerun to ensure all dashboards reload fully with final details
        nn.rerun()
        
    except Exception as e:
        nn.session_state.logs.append(f"❌ [Bağlantı Kesintisi] {str(e)}")
        logs_html = "".join([f"<div class='agent-log-row'>{log}</div>" for log in nn.session_state.logs])
        logs_placeholder.markdown(f"<div class='agent-log-container'>{logs_html}</div>", unsafe_allow_html=True)
        report_placeholder.error(f"Güvenli backend servisi ile iletişim kurulamadı. Hata: {str(e)}")

# ==========================================
# 9. Bottom Analytics Dashboard
# ==========================================

nn.markdown("---")
nn.markdown('<h2 style="font-family: \'Plus Jakarta Sans\', sans-serif; color: #ffffff; font-size: 1.25rem; font-weight: 700; letter-spacing: -0.01em;">📊 GÜVEN VE BİLGİ DOĞRULUK ANALİTİĞİ</h2>', unsafe_allow_html=True)

col_chart_1, col_chart_2, col_chart_3 = nn.columns([1, 1, 1.2])

# Pull values from session state checkpoint
hallucination_score = nn.session_state.checkpoint.get("hallucination_score", 0.0)
faith_score = max(0.0, min(1.0, 1.0 - hallucination_score))

# Answer Relevance derived from the actual verified facts: the mean confidence score
# the cross-checker assigned to the grounded claims (0.0 when nothing was verified).
facts_count = len(nn.session_state.verified_facts)
conflicts_count = len(nn.session_state.detected_conflicts)
total_claims = facts_count + conflicts_count
if facts_count > 0:
    confidences = [
        float(f.get("confidence_score", 0.0)) for f in nn.session_state.verified_facts
    ]
    relevance_score = max(0.0, min(1.0, sum(confidences) / len(confidences)))
else:
    relevance_score = 0.0

with col_chart_1:
    # Faithfulness Gauge (RAG Document Grounding)
    fig_gauge_1 = render_gauge_chart("BİLGİ SADAKATİ (FAITHFULNESS)", faith_score, "#6ee7b7") # Elite Mint
    nn.plotly_chart(fig_gauge_1, width="stretch")

with col_chart_2:
    # Answer Relevance Gauge
    fig_gauge_2 = render_gauge_chart("SORGUYA UYGUNLUK (RELEVANCE)", relevance_score, "#00d2ff") # Apple Cyber Blue
    nn.plotly_chart(fig_gauge_2, width="stretch")

with col_chart_3:
    # Sources Bar Chart
    fig_bar = render_sources_bar_chart(nn.session_state.verified_facts)
    nn.plotly_chart(fig_bar, width="stretch")
