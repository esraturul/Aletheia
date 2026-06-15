#!/usr/bin/env python3
"""
Aletheia Agent and Conflict Topology Graph Page
Description:
    Visualizes the multi-agent execution pipeline and semantic RAG relationships.
    Uses custom Plotly network topologies to draw nodes representing agents,
    queries, facts, and conflicts, connected by colored edges (indigo for agents, green for facts, rose for conflicts).
    Redesigned to meet modern Premium Enterprise SaaS guidelines.
"""

import os
import streamlit as nn
import plotly.graph_objects as go

# Set Page Config
nn.set_page_config(
    page_title="ALETHEIA // AGENT TOPOLOGY",
    page_icon="🕸️",
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
nn.markdown('<h1 class="cyber-title">🕸️ KONSENSÜS AĞI & MUTABAKAT TOPOLOJİSİ</h1>', unsafe_allow_html=True)
nn.markdown('<p class="cyber-subtitle">ALETHEIA ÇOK AJANLI MUTABAKAT SÜRECİ VE ÇAPRAZ ÇELİŞKİ TOPOLOJİ ANALİZİ</p>', unsafe_allow_html=True)

# 2. Sidebar info
nn.sidebar.markdown("## 🕸️ TOPOLOJİ SİSTEMİ")
nn.sidebar.info(
    "Bu interaktif harita, araştırma sorgusunun ajanlar tarafından nasıl işlendiğini ve "
    "elde edilen veri dökümanlarındaki hakikatler ile çelişkilerin ilişkisel ağını gösterir."
)

# Legend cards (SaaS styling)
nn.markdown("### 🟢 KONSENSÜS AĞ GÖSTERGELERİ")
leg_col1, leg_col2, leg_col3, leg_col4 = nn.columns(4)

with leg_col1:
    nn.markdown(
        '<div class="cyber-card" style="border-left: 3px solid #6366f1; padding: 10px;">'
        '<span style="color:#6366f1; font-weight:bold; font-family:\'Plus Jakarta Sans\'; font-size: 0.9rem;">🔍 SORGULAMA MERKEZİ</span><br>'
        '<span style="font-size:0.8rem; color:#94a3b8;">Kullanıcının doğrulama talebi.</span>'
        '</div>',
        unsafe_allow_html=True
    )
with leg_col2:
    nn.markdown(
        '<div class="cyber-card" style="border-left: 3px solid #a5b4fc; padding: 10px;">'
        '<span style="color:#a5b4fc; font-weight:bold; font-family:\'Plus Jakarta Sans\'; font-size: 0.9rem;">🤖 CANLI AJANLAR</span><br>'
        '<span style="font-size:0.8rem; color:#94a3b8;">Veri toplayan ve denetleyen yapılar.</span>'
        '</div>',
        unsafe_allow_html=True
    )
with leg_col3:
    nn.markdown(
        '<div class="cyber-card" style="border-left: 3px solid #10b981; padding: 10px;">'
        '<span style="color:#10b981; font-weight:bold; font-family:\'Plus Jakarta Sans\'; font-size: 0.9rem;">📜 MUTABAKAT VERİLERİ</span><br>'
        '<span style="font-size:0.8rem; color:#94a3b8;">ChromaDB\'de eşleşen kanıt belgeleri.</span>'
        '</div>',
        unsafe_allow_html=True
    )
with leg_col4:
    nn.markdown(
        '<div class="cyber-card" style="border-left: 3px solid #f43f5e; padding: 10px;">'
        '<span style="color:#f43f5e; font-weight:bold; font-family:\'Plus Jakarta Sans\'; font-size: 0.9rem;">⚠️ BULUNAN ÇELİŞKİLER</span><br>'
        '<span style="font-size:0.8rem; color:#94a3b8;">Veriler arasındaki rakamsal/metodolojik uyuşmazlık.</span>'
        '</div>',
        unsafe_allow_html=True
    )

nn.markdown("<br>", unsafe_allow_html=True)

# 3. Design Plotly Network coordinates
node_coords = {
    0: (0.0, 0.0),       # Central Query
    1: (-1.5, 0.8),     # Scraper Agent
    2: (1.5, 0.8),      # Cross-Checker Agent
    3: (1.5, -0.8),     # Fact-Checker Agent
    4: (-1.5, -0.8),    # Reporter Agent
    5: (3.0, 1.2),      # TÜİK Source Doc
    6: (3.0, 0.0),      # ENAG Source Doc
    7: (3.0, -1.2),     # Reuters Source Doc
    8: (0.0, 1.6)       # Conflict node
}

# Define edges grouping
agent_edges = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 0)]
fact_edges = [(1, 5), (1, 6), (1, 7)]
conflict_edges = [(5, 8), (6, 8)]

def make_edge_trace(edges, color, name, dash=None, width=2):
    edge_x = []
    edge_y = []
    for edge in edges:
        x0, y0 = node_coords[edge[0]]
        x1, y1 = node_coords[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    return go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=width, color=color, dash=dash),
        hoverinfo='none',
        mode='lines',
        name=name
    )

# Create Plotly traces for Edges (SaaS styling)
agent_edges_trace = make_edge_trace(agent_edges, 'rgba(99, 102, 241, 0.45)', 'Ajan Akış Yolu', dash='dash', width=2)
fact_edges_trace = make_edge_trace(fact_edges, 'rgba(16, 185, 129, 0.55)', 'Doğrulanmış Kaynak Bağlantısı', width=2)
conflict_edges_trace = make_edge_trace(conflict_edges, 'rgba(244, 63, 94, 0.75)', 'Uyuşmazlık Çelişki Köprüsü', width=3)

# Create Node Traces by Group to enable gorgeous styled shapes & colors
query_node_trace = go.Scatter(
    x=[node_coords[0][0]], y=[node_coords[0][1]],
    mode='markers+text',
    marker=dict(size=40, color='#6366f1', line=dict(width=2, color='#ffffff'), symbol='circle'),
    text=["🔍 SORGULAMA MERKEZİ"],
    textposition="bottom center",
    hovertext="<b>Araştırma Sorgusu:</b> Enflasyon Veri Analizi<br>Metin: TÜİK vs ENAG 2025 yılı uyuşmazlığı.",
    hoverinfo='text',
    name='Kullanıcı Sorgusu'
)

agent_nodes_trace = go.Scatter(
    x=[node_coords[1][0], node_coords[2][0], node_coords[3][0], node_coords[4][0]],
    y=[node_coords[1][1], node_coords[2][1], node_coords[3][1], node_coords[4][1]],
    mode='markers+text',
    marker=dict(size=30, color='#a5b4fc', line=dict(width=1.5, color='#0f172a'), symbol='square'),
    text=["🤖 SCRAPER", "🤖 CROSS-CHECKER", "🤖 FACT-CHECKER", "🤖 REPORTER"],
    textposition="top center",
    hovertext=[
        "<b>Scraper Ajanı:</b> Web ve canlı haber verilerini toplayıp ChromaDB RAG'e yükler.",
        "<b>Cross-Checker Ajanı:</b> Verileri karşılaştırır, numeric/temporal çelişkileri bulur.",
        "<b>Fact-Checker Ajanı:</b> Üretilen iddiaları denetler, sadakat skoru hesaplar.",
        "<b>Reporter Ajanı:</b> Doğrulanmış gerçeklerden premium nihai rapor oluşturur."
    ],
    hoverinfo='text',
    name='Aktif Aletheia Ajanları'
)

fact_nodes_trace = go.Scatter(
    x=[node_coords[5][0], node_coords[6][0], node_coords[7][0]],
    y=[node_coords[5][1], node_coords[6][1], node_coords[7][1]],
    mode='markers+text',
    marker=dict(size=22, color='#10b981', line=dict(width=1, color='#0f172a'), symbol='hexagon'),
    text=["📜 TÜİK BÜLTENİ [1]", "📜 ENAG RAPORU [2]", "📜 REUTERS ANALİZİ [3]"],
    textposition="middle right",
    hovertext=[
        "<b>Resmi Veri Kaynağı [1]:</b> TÜİK 2025 Yıllık Enflasyon Beyanı (%45.8)",
        "<b>Bağımsız Veri Kaynağı [2]:</b> ENAG 2025 Yıllık Enflasyon Raporu (%112.4)",
        "<b>Medya/Finans Analizi [3]:</b> Reuters 2026 Türkiye Makroekonomi Analizi Raporu"
    ],
    hoverinfo='text',
    name='Doğrulanan Kaynaklar'
)

conflict_nodes_trace = go.Scatter(
    x=[node_coords[8][0]], y=[node_coords[8][1]],
    mode='markers+text',
    marker=dict(size=32, color='#f43f5e', line=dict(width=2, color='#ffffff'), symbol='diamond'),
    text=["🚨 %66.6 BİLGİ UYUŞMAZLIĞI"],
    textposition="top center",
    hovertext="<b>Derin Çelişki Tespit Edildi!</b><br>TÜİK resmi oranı %45.8 iken ENAG akademisyen ölçümü %112.4'tür.<br>Net Makas: %66.6 uyuşmazlık.",
    hoverinfo='text',
    name='Tespit Edilen Çelişkiler'
)

# 4. Assemble Figure Layout
fig = go.Figure(data=[
    agent_edges_trace, fact_edges_trace, conflict_edges_trace,
    query_node_trace, agent_nodes_trace, fact_nodes_trace, conflict_nodes_trace
])

fig.update_layout(
    title=dict(
        text="ALETHEIA KONSENSÜS VE BİLGİ MUTABAKAT TOPOLOJİSİ",
        font=dict(color='#ffffff', family='Plus Jakarta Sans', size=15, weight='bold'),
        x=0.5, y=0.98
    ),
    showlegend=True,
    legend=dict(
        font=dict(color='#94a3b8', size=10),
        bgcolor='rgba(15,17,26,0.85)',
        bordercolor='rgba(255,255,255,0.06)',
        borderwidth=1,
        x=0.01, y=0.01
    ),
    paper_bgcolor='rgba(18, 22, 33, 0.65)',
    plot_bgcolor='rgba(0, 0, 0, 0)',
    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
    height=600,
    margin=dict(l=40, r=40, t=60, b=40)
)

# Render Plotly Network Canvas
nn.markdown("### 🕸️ ETKİLEŞİMLİ AĞ HARİTASI")
with nn.container():
    nn.markdown('<div class="cyber-card" style="padding: 10px;">', unsafe_allow_html=True)
    nn.plotly_chart(fig, width="stretch")
    nn.markdown('</div>', unsafe_allow_html=True)

# Graph Topology explanations
nn.markdown("### 🔍 MANTIKSAL ANALİZ AKIŞI VE MUTABAKAT")
nn.markdown(
    '<div class="cyber-card">'
    '<ul>'
    '<li><b>Ajan Konsensüsü:</b> Kullanıcı bir arama başlattığında sorgu <b>Scraper Ajanı</b>\'na aktarılır. Scraper verileri toplar, semantize eder ve RAG veritabanımıza yazar.</li>'
    '<li><b>Çapraz Karşılaştırma:</b> <b>Cross-Checker Ajanı</b> dökümanları tarar ve <b>TÜİK (%45.8)</b> ile <b>ENAG (%112.4)</b> arasındaki <b>%66.6\'lık</b> radikal uçurumu (Çelişki Düğümü) tespit ederek topolojiye rose (gül kurusu) uyuşmazlık köprüsünü çizer.</li>'
    '<li><b>Anti-Halüsinasyon Denetimi:</b> <b>Fact-Checker Ajanı</b> sentezlenen tüm hakikat beyanlarının dökümanlarla birebir örtüştüğünü doğrular ve <b>sadakat skoru %95</b> olarak haritaya zümrüt yeşili kaynak bağlarını ekler.</li>'
    '</ul>'
    '</div>',
    unsafe_allow_html=True
)
