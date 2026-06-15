#!/usr/bin/env python3
"""
Aletheia LLMOps and Performance Analytics Page

Description:
    Renders the monitoring & compliance statistics for the multi-agent system.
    Plots agent latency, accumulated execution costs, and historical faithfulness trends.
    Redesigned to meet modern Premium Enterprise SaaS guidelines.
"""

import os
import streamlit as nn
import plotly.graph_objects as go

# Set Page Config
nn.set_page_config(
    page_title="ALETHEIA // LLMOPS METRICS",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 1. Inject Premium CSS Styling Custom overrides
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
css_path = os.path.join(root_dir, "assets", "style.css")

if os.path.exists(css_path):
    with open(css_path, "r", encoding="utf-8") as f:
        css_data = f.read()
    nn.markdown(f"<style>{css_data}</style>", unsafe_allow_html=True)
else:
    nn.warning("style.css stylesheet not found under frontend/assets/.")

# Titles
nn.markdown('<h1 class="cyber-title">📈 SYSTEM PERFORMANCE & LLMOPS ANALYTICS</h1>', unsafe_allow_html=True)
nn.markdown('<p class="cyber-subtitle">ALETHEIA SİSTEM GECİKME, OPERASYONEL TOKEN MALİYETİ VE ANALİZ GÜVENİLİRLİK ANALİTİKLERİ</p>', unsafe_allow_html=True)

# 2. Sidebar Info
nn.sidebar.markdown("## 📈 LLMOPS İSTATİSTİKLERİ")
nn.sidebar.info(
    "Bu panel, Aletheia siteminin çalışma hızını, finansal maliyetini ve doğruluk "
    "performansını anlık ve tarihsel olarak denetlemenizi sağlar."
)

# 3. Render Top Metrics Row (Premium SaaS Design)
nn.markdown("### 📊 SİSTEM PERFORMANS & MALİYET ÖZETİ")
m_col1, m_col2, m_col3, m_col4 = nn.columns(4)

with m_col1:
    nn.markdown(
        '<div class="cyber-card" style="text-align: center;">'
        '<div style="font-family: \'Plus Jakarta Sans\', sans-serif; font-size: 0.85rem; color: #94a3b8; font-weight:600; letter-spacing:1px;">ORTALAMA ANALİZ SÜRESİ</div>'
        '<div style="font-family: \'Plus Jakarta Sans\', sans-serif; font-size: 2rem; color: #6366f1; font-weight: bold; margin-top: 5px;">9.6 sn</div>'
        '</div>',
        unsafe_allow_html=True
    )
with m_col2:
    nn.markdown(
        '<div class="cyber-card" style="text-align: center;">'
        '<div style="font-family: \'Plus Jakarta Sans\', sans-serif; font-size: 0.85rem; color: #94a3b8; font-weight:600; letter-spacing:1px;">KÜMÜLATİF MALİYET (USD)</div>'
        '<div style="font-family: \'Plus Jakarta Sans\', sans-serif; font-size: 2rem; color: #f43f5e; font-weight: bold; margin-top: 5px;">$0.048</div>'
        '</div>',
        unsafe_allow_html=True
    )
with m_col3:
    nn.markdown(
        '<div class="cyber-card" style="text-align: center;">'
        '<div style="font-family: \'Plus Jakarta Sans\', sans-serif; font-size: 0.85rem; color: #94a3b8; font-weight:600; letter-spacing:1px;">LOKAL SAAS TASARRUFU</div>'
        '<div style="font-family: \'Plus Jakarta Sans\', sans-serif; font-size: 2rem; color: #10b981; font-weight: bold; margin-top: 5px;">%100</div>'
        '</div>',
        unsafe_allow_html=True
    )
with m_col4:
    nn.markdown(
        '<div class="cyber-card" style="text-align: center;">'
        '<div style="font-family: \'Plus Jakarta Sans\', sans-serif; font-size: 0.85rem; color: #94a3b8; font-weight:600; letter-spacing:1px;">ORTALAMA SADAKAT (FAITHFULNESS)</div>'
        '<div style="font-family: \'Plus Jakarta Sans\', sans-serif; font-size: 2rem; color: #10b981; font-weight: bold; margin-top: 5px;">%95.0</div>'
        '</div>',
        unsafe_allow_html=True
    )

nn.markdown("<br>", unsafe_allow_html=True)

# 4. Latency Analysis Layout (Horizontal Bar Chart)
lat_col, cost_col = nn.columns([1, 1])

with lat_col:
    nn.markdown("### ⏱️ AJAN GECİKME ANALİZLERİ (LATENCY)")
    
    # Latency data
    y_agents = ["Reporter Agent", "Fact-Checker", "Cross-Checker", "Scraper Agent"]
    x_latency = [1.8, 1.5, 2.1, 4.2]
    
    fig_lat = go.Figure(go.Bar(
        x=x_latency,
        y=y_agents,
        orientation='h',
        marker=dict(color='#818cf8', line=dict(color='rgba(0,0,0,0)', width=0)),  # Soft SaaS Violet
        hoverinfo='x',
        text=[f"{val} sn" for val in x_latency],
        textposition='auto'
    ))
    
    fig_lat.update_layout(
        paper_bgcolor='rgba(18, 22, 33, 0.65)',
        plot_bgcolor='rgba(0, 0, 0, 0)',
        font=dict(color='#e2e8f0', family='Inter'),
        xaxis=dict(title="Gecikme (Saniye)", gridcolor='rgba(255,255,255,0.03)', zeroline=False),
        yaxis=dict(gridcolor='rgba(0,0,0,0)'),
        height=320,
        margin=dict(l=20, r=20, t=20, b=20)
    )
    
    nn.markdown('<div class="cyber-card" style="padding: 10px;">', unsafe_allow_html=True)
    nn.plotly_chart(fig_lat, width="stretch")
    nn.markdown('</div>', unsafe_allow_html=True)

# 5. Cost Analysis Layout (Double Line Chart)
with cost_col:
    nn.markdown("### 💸 BİRİKİMLİ API MALİYETİ & LOKAL TASARRUF")
    
    # Cost data
    queries = ["Sorgu 1", "Sorgu 2", "Sorgu 3", "Sorgu 4", "Sorgu 5", "Sorgu 6", "Sorgu 7"]
    openai_cost = [0.008, 0.015, 0.023, 0.030, 0.038, 0.045, 0.052]
    ollama_cost = [0.000, 0.000, 0.000, 0.000, 0.000, 0.000, 0.000]
    
    fig_cost = go.Figure()
    fig_cost.add_trace(go.Scatter(
        x=queries, y=openai_cost,
        mode='lines+markers',
        name='OpenAI API Tahmini Bulut Maliyeti',
        line=dict(color='#f43f5e', width=3),  # Coral Rose accent
        marker=dict(size=7)
    ))
    fig_cost.add_trace(go.Scatter(
        x=queries, y=ollama_cost,
        mode='lines+markers',
        name='Lokal Ollama / Kurumsal Tasarruf',
        line=dict(color='#6366f1', width=3),  # Premium SaaS Indigo
        marker=dict(size=7)
    ))
    
    fig_cost.update_layout(
        paper_bgcolor='rgba(18, 22, 33, 0.65)',
        plot_bgcolor='rgba(0, 0, 0, 0)',
        font=dict(color='#e2e8f0', family='Inter'),
        xaxis=dict(gridcolor='rgba(255,255,255,0.03)', zeroline=False),
        yaxis=dict(title="Birikimli Maliyet (USD)", gridcolor='rgba(255,255,255,0.03)', zeroline=False),
        legend=dict(x=0.02, y=0.98, bgcolor='rgba(15,17,26,0.85)', bordercolor='rgba(255,255,255,0.06)', borderwidth=1),
        height=320,
        margin=dict(l=20, r=20, t=20, b=20)
    )
    
    nn.markdown('<div class="cyber-card" style="padding: 10px;">', unsafe_allow_html=True)
    nn.plotly_chart(fig_cost, width="stretch")
    nn.markdown('</div>', unsafe_allow_html=True)

nn.markdown("<br>", unsafe_allow_html=True)

# 6. Quality/Faithfulness Trend Chart (Single Line Chart)
nn.markdown("### 🛡️ DOĞRULUK VE BİLGİ SADAKATİ TREND ANALİZLERİ (FAITHFULNESS)")
with nn.container():
    # Faithfulness score trend
    faith_trend = [0.85, 0.90, 0.88, 0.95, 0.92, 0.95, 0.95]
    
    fig_faith = go.Figure()
    fig_faith.add_trace(go.Scatter(
        x=queries, y=faith_trend,
        mode='lines+markers+text',
        name='Doğruluk Sadakat Skoru',
        line=dict(color='#10b981', width=3.5),  # Refined Emerald Green
        marker=dict(size=8, color='#10b981', line=dict(color='#ffffff', width=1.5)),
        text=[f"%{val*100:.0f}" for val in faith_trend],
        textposition="top center"
    ))
    
    # Target Threshold horizontal reference line
    fig_faith.add_shape(
        type="line",
        x0=queries[0], y0=0.85,
        x1=queries[-1], y1=0.85,
        line=dict(color="rgba(244, 63, 94, 0.4)", width=2, dash="dash"),  # Rose safety reference line
        name="Güvenlik Eşiği (%85)"
    )
    
    fig_faith.update_layout(
        paper_bgcolor='rgba(18, 22, 33, 0.65)',
        plot_bgcolor='rgba(0, 0, 0, 0)',
        font=dict(color='#e2e8f0', family='Inter'),
        xaxis=dict(gridcolor='rgba(255,255,255,0.03)', zeroline=False),
        yaxis=dict(title="Sadakat Skoru (0.0 - 1.0)", gridcolor='rgba(255,255,255,0.03)', zeroline=False, range=[0.5, 1.05]),
        height=320,
        margin=dict(l=20, r=20, t=30, b=20)
    )
    
    nn.markdown('<div class="cyber-card" style="padding: 10px;">', unsafe_allow_html=True)
    nn.plotly_chart(fig_faith, width="stretch")
    nn.markdown('</div>', unsafe_allow_html=True)
