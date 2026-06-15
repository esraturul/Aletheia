#!/usr/bin/env python3
"""
Aletheia Knowledge Base and Vector Store Manager Page

Description:
    Provides direct visibility into the ChromaDB persistent index.
    Displays metrics, active source URLs, chunk aggregations, and handles
    live file uploads (.txt / .pdf) for real-time document chunking & indexing.
    Redesigned to meet modern Premium Enterprise SaaS guidelines.
"""

import os
import sys
import pandas as pd
import streamlit as nn

# Set Streamlit Page Configuration with consistent styling
nn.set_page_config(
    page_title="ALETHEIA // KNOWLEDGE BASE",
    page_icon="📂",
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

# 2. Add root path to sys.path to resolve backend imports
if root_dir not in sys.path:
    sys.path.append(root_dir)

from backend.app.rag_engine import AletheiaRAGEngine

# Title headers
nn.markdown('<h1 class="cyber-title">📂 BİLGİ BANKASI VE DÖKÜMAN YÖNETİMİ</h1>', unsafe_allow_html=True)
nn.markdown('<p class="cyber-subtitle">ALETHEIA KURUMSAL BELGE HAVUZU VE VEKTÖR VERİTABANI İNDEKS DENETLEYİCİSİ</p>', unsafe_allow_html=True)

# 3. Initialize RAG Engine
try:
    rag = AletheiaRAGEngine(db_path=os.path.join(root_dir, "chroma_db"))
except Exception as e:
    nn.error(f"Vektör veritabanına bağlantı kurulamadı: {e}")
    st.stop()

# 4. Sidebar Database Operations
nn.sidebar.markdown("## ⚙️ BİLGİ ÜSSÜ İŞLEMLERİ")
nn.sidebar.info("Buradan Aletheia RAG veritabanını izleyebilir, yeni veri yükleyebilir ve vektör belleğini sıfırlayabilirsiniz.")

if nn.sidebar.button("🚨 VEKTÖR BELLEĞİNİ SIFIRLA"):
    with nn.spinner("Veritabanı siliniyor..."):
        if rag.clear_database():
            nn.sidebar.success("ChromaDB başarıyla temizlendi!")
            nn.rerun()
        else:
            nn.sidebar.error("Veritabanı sıfırlanamadı.")

# 5. Load and Aggregate Chromadb Data
collection_data = rag.collection.get()
total_chunks = len(collection_data.get("ids", []))

sources_agg = {}
if total_chunks > 0:
    ids = collection_data.get("ids", [])
    metadatas = collection_data.get("metadatas", [])
    documents = collection_data.get("documents", [])
    
    for idx in range(total_chunks):
        meta = metadatas[idx] or {}
        src = meta.get("source_url", "Bilinmeyen Kaynak")
        trust = float(meta.get("initial_trust_score", 1.0))
        ts = meta.get("timestamp", "Bilinmeyen Zaman")
        doc_text = documents[idx] or ""
        
        if src not in sources_agg:
            sources_agg[src] = {
                "source": src,
                "chunks": 0,
                "trust_score": trust,
                "timestamp": ts,
                "snippet": doc_text[:90] + "..." if len(doc_text) > 90 else doc_text
            }
        sources_agg[src]["chunks"] += 1

unique_sources = len(sources_agg)
avg_trust = (
    sum(s["trust_score"] for s in sources_agg.values()) / unique_sources
    if unique_sources > 0
    else 0.0
)

# 6. Render Metrics Overview (Rounded Glassmorphism layout)
nn.markdown("### 📊 VERİ HAVUZU İSTATİSTİKLERİ")
metric_col1, metric_col2, metric_col3 = nn.columns(3)

with metric_col1:
    nn.markdown(
        f'<div class="cyber-card" style="text-align: center;">'
        f'<div style="font-family: \'Plus Jakarta Sans\', sans-serif; font-size: 0.85rem; color: #94a3b8; font-weight:600; letter-spacing:1px;">TOPLAM VERİ PARÇASI (CHUNKS)</div>'
        f'<div style="font-family: \'Plus Jakarta Sans\', sans-serif; font-size: 2.2rem; color: #10b981; font-weight: bold; margin-top: 5px;">{total_chunks}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

with metric_col2:
    nn.markdown(
        f'<div class="cyber-card" style="text-align: center;">'
        f'<div style="font-family: \'Plus Jakarta Sans\', sans-serif; font-size: 0.85rem; color: #94a3b8; font-weight:600; letter-spacing:1px;">BENZERSİZ KAYNAK / BELGE</div>'
        f'<div style="font-family: \'Plus Jakarta Sans\', sans-serif; font-size: 2.2rem; color: #6366f1; font-weight: bold; margin-top: 5px;">{unique_sources}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

with metric_col3:
    nn.markdown(
        f'<div class="cyber-card" style="text-align: center;">'
        f'<div style="font-family: \'Plus Jakarta Sans\', sans-serif; font-size: 0.85rem; color: #94a3b8; font-weight:600; letter-spacing:1px;">ORTALAMA GÜVEN SKORU</div>'
        f'<div style="font-family: \'Plus Jakarta Sans\', sans-serif; font-size: 2.2rem; color: #10b981; font-weight: bold; margin-top: 5px;">%{avg_trust*100:.1f}</div>'
        f'</div>',
        unsafe_allow_html=True
    )

nn.markdown("<br>", unsafe_allow_html=True)

# 7. File Uploader and Indexing
nn.markdown("### 📥 DÖKÜMAN EKLE VE İNDEKSLE")
with nn.container():
    nn.markdown('<div class="cyber-card">', unsafe_allow_html=True)
    uploaded_file = nn.file_uploader("İndekslemek istediğiniz metin belgesini (.txt) veya analiz raporunu (.pdf) seçin:", type=["txt", "pdf"])
    
    if uploaded_file is not None:
        file_name = uploaded_file.name
        with nn.spinner(f"'{file_name}' işleniyor ve vektör veritabanına indeksleniyor..."):
            text_content = ""
            read_success = False
            
            if file_name.endswith(".txt"):
                try:
                    text_content = uploaded_file.read().decode("utf-8")
                    read_success = True
                except Exception as read_err:
                    nn.error(f"Dosya okunamadı: {read_err}")
                    
            elif file_name.endswith(".pdf"):
                try:
                    import pypdf
                    pdf_reader = pypdf.PdfReader(uploaded_file)
                    extracted_pages = []
                    for idx, page in enumerate(pdf_reader.pages):
                        extracted_pages.append(page.extract_text() or "")
                    text_content = "\n".join(extracted_pages)
                    read_success = True
                except ImportError:
                    nn.error(
                        "⚠️ PDF dosyalarını işlemek için 'pypdf' kütüphanesi yüklü olmalıdır.\n"
                        "Lütfen terminalde 'pip install pypdf' çalıştırın veya şimdilik '.txt' formatında dosya yükleyin."
                    )
                except Exception as read_err:
                    nn.error(f"PDF dosyası okunurken hata oluştu: {read_err}")
            
            if read_success and text_content.strip():
                # Prepare document entry
                from datetime import datetime
                new_doc = {
                    "text": text_content,
                    "source_url": file_name,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "initial_trust_score": 1.0
                }
                
                # Index document
                if rag.add_documents([new_doc]):
                    nn.success(f"🟢 '{file_name}' başarıyla ayrıştırıldı ve RAG Vektör Veritabanına indekslendi! Ajanlar artık bu yeni verileri de sorgulayabilir.")
                    nn.rerun()
                else:
                    nn.error("İndeksleme işlemi sırasında teknik bir hata oluştu.")
                    
    nn.markdown('</div>', unsafe_allow_html=True)

nn.markdown("<br>", unsafe_allow_html=True)

# 8. Document Listing Table
nn.markdown("### 🗄️ AKTİF KURUMSAL DÖKÜMAN VE KAYNAKLAR")
if unique_sources > 0:
    # Convert aggregated sources dict into a beautifully formatted pandas DataFrame
    df_list = list(sources_agg.values())
    df = pd.DataFrame(df_list)
    
    # Select and rename columns for corporate look
    df_display = df[["source", "chunks", "trust_score", "timestamp", "snippet"]].copy()
    df_display.columns = [
        "Kaynak URL / Belge Adı",
        "Parça Sayısı (Chunks)",
        "Güven Endeksi",
        "Kayıt Tarihi",
        "İçerik Kesiti"
    ]
    
    # Render table inside styled container
    nn.dataframe(df_display, use_container_width=True)
else:
    nn.info("Vektör veritabanında henüz indekslenmiş bir döküman bulunmamaktadır. Yukarıdaki panelden dosya yükleyebilir veya ana sayfadan doğrulama başlatabilirsiniz.")
