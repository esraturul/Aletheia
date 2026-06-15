#!/usr/bin/env python3
"""
Aletheia Multi-Agent System Definition

Description:
    Defines agent personas, prompts, Pydantic schemas for verification, 
    and bridges LLM calls with RAG and MCP tools.
"""

import os
import sys
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# Ensure the parent directory is in the path to import mcp_servers
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Tools are invoked over the Model Context Protocol via the MCP client bridge
# (with automatic in-process fallback if a server cannot be reached).
from mcp_servers.mcp_client import mcp_search_web, mcp_fetch_live_news

# Configure logging
logger = logging.getLogger("AletheiaAgents")

# ==========================================
# 1. Pydantic Verification Schemas
# ==========================================

class DetectedConflict(BaseModel):
    title: str = Field(description="Çelişkinin kısa ve çarpıcı başlığı")
    description: str = Field(description="Bulunan çelişkinin detaylı açıklaması, sayılar veya tarihler arasındaki uyumsuzluk")
    sources: List[str] = Field(description="Bu çelişkiye sebep olan kaynak URL'leri")

class VerifiedFact(BaseModel):
    statement: str = Field(description="Herhangi bir spekülasyon veya halüsinasyon içermeyen, doğrulanmış net bilgi cümlesi")
    confidence_score: float = Field(description="Bilginin doğruluk güven skoru (0.0 ile 1.0 arası)")
    sources: List[str] = Field(description="Bu bilgiyi destekleyen ve doğrulayan kaynak URL'lerin listesi")
    counter_claims: Optional[List[str]] = Field(default=[], description="Bu bilgiye karşı sürülen ama çürütülmüş/elenmiş iddialar")

class AletheiaReport(BaseModel):
    summary: str = Field(description="Sorgulanan konunun genel doğrulama ve analiz özeti")
    facts: List[VerifiedFact] = Field(description="Doğrulanmış ve kesinleşmiş gerçekler listesi")
    conflicts: List[DetectedConflict] = Field(description="Kaynaklar arasında tespit edilen çelişkiler listesi")

# ==========================================
# 2. LLM Initialization and Factory
# ==========================================

def _extract_context_block(messages) -> str:
    """
    Best-effort extraction of the RAG context text from the prompt messages so the
    mock can ground its simulated output in whatever was actually retrieved,
    instead of returning a hardcoded topic.
    """
    try:
        if isinstance(messages, str):
            return messages
        text = ""
        for m in messages:
            if isinstance(m, dict):
                text += str(m.get("content", "")) + "\n"
            else:
                text += str(getattr(m, "content", m)) + "\n"
        return text
    except Exception:
        return ""


class MockStructuredLLM:
    """
    Simulates a structured-output Chat LLM for zero-key local demos.
    Grounds its simulated facts/conflicts in the retrieved context that is present
    in the prompt, so the output reflects the actual query rather than a fixed topic.
    """
    def __init__(self, schema):
        self.schema = schema

    def invoke(self, messages):
        schema_name = self.schema.__name__
        logger.info(f"[AletheiaMockLLM] Simulating structured output for: {schema_name}")
        context = _extract_context_block(messages)

        if schema_name == "AletheiaReport":
            # Derive a short snippet from the retrieved context to ground the demo output.
            snippet = " ".join(context.split())[:240] if context.strip() else ""
            if snippet:
                fact_statement = (
                    "Çekilen kaynaklarda konuyla ilgili şu bağlam doğrulanmıştır: "
                    f"\"{snippet}...\""
                )
                summary = (
                    "Yerel demo modunda (LLM anahtarı yok) çalışılıyor. Aşağıdaki bulgular, "
                    "RAG veritabanına indekslenen canlı kaynaklardan türetilmiştir."
                )
            else:
                fact_statement = (
                    "Bağlam bulunamadı; canlı kaynaklardan indekslenebilir veri elde edilemedi."
                )
                summary = "Yerel demo modunda çalışılıyor ve RAG bağlamı boş döndü."

            return AletheiaReport(
                summary=summary,
                facts=[
                    VerifiedFact(
                        statement=fact_statement,
                        confidence_score=0.80,
                        sources=["Web Search Scraper", "Live News Feeds"],
                        counter_claims=[],
                    )
                ],
                conflicts=[],
            )
        elif schema_name == "FaithfulnessEvaluation":
            # For our guardrail faithfulness checks
            from backend.app.guardrails import FaithfulnessEvaluation
            return FaithfulnessEvaluation(
                faithfulness_score=0.90,
                reasoning="Demo modunda üretilen bulgular doğrudan RAG bağlamından türetildiği için yüksek sadakatli kabul edilmiştir.",
            )
        else:
            return self.schema()


class AletheiaMockLLM:
    """
    A custom mock Chat LLM that natively implements with_structured_output
    to provide zero-key local demonstrations grounded in the retrieved context.
    """
    def with_structured_output(self, schema):
        return MockStructuredLLM(schema)

    def invoke(self, messages):
        logger.info("[AletheiaMockLLM] Simulating Markdown Synthesis Report...")
        context = _extract_context_block(messages)
        # Surface whatever facts/conflicts were threaded into the reporter prompt.
        body = context.strip() or "Görüntülenecek doğrulanmış veri bulunamadı."
        mock_markdown_report = (
            "# 🛡️ ALETHEIA // DOĞRULAMA VE ARAŞTIRMA RAPORU\n\n"
            "## 📊 GENEL DURUM\n"
            "*Yerel demo modunda (LLM anahtarı yapılandırılmadı) çalışılıyor.* "
            "Aşağıdaki içerik, ajanların canlı kaynaklardan derleyip doğruladığı verilerden sentezlenmiştir.\n\n"
            "---\n\n"
            "## 📜 DERLENEN DOĞRULAMA İÇERİĞİ\n\n"
            f"{body}\n\n"
            "---\n\n"
            "## 🛡️ SİSTEM NOTU\n"
            "*Gerçek LLM sentezi için OPENAI_API_KEY tanımlayın; bu çıktı yerel mock üreticisinden gelmektedir.*\n"
        )
        from langchain_core.messages import AIMessage
        return AIMessage(content=mock_markdown_report)

def get_llm(temperature: float = 0.0):
    """
    Returns a LangChain LLM instance. 
    Prioritizes OpenAI (gpt-4o-mini) and falls back to local Ollama (llama3) if key is missing.
    """
    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        logger.info("Initializing OpenAI gpt-4o-mini...")
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-4o-mini", temperature=temperature, api_key=openai_key)
    else:
        logger.warning("OPENAI_API_KEY not found. Attempting to fall back to Ollama (llama3)...")
        try:
            from langchain_community.chat_models import ChatOllama
            return ChatOllama(model="llama3", temperature=temperature)
        except Exception as e:
            logger.error(f"Failed to load Ollama client: {e}. Loading premium AletheiaMockLLM local demo wrapper.")
            return AletheiaMockLLM()

# ==========================================
# 3. Agent Functions
# ==========================================

def run_scraper_agent(query: str, rag_engine: Any, use_web: bool = True, use_news: bool = True) -> Dict[str, Any]:
    """
    Scraper Agent:
    Queries the MCP Search and News servers (over the protocol), compiles retrieved
    documents, and indexes them into the RAG database.

    Args:
        use_web: Enable the web search MCP integration.
        use_news: Enable the live news MCP integration.
    """
    logs = []
    logger.info("Scraper Agent started working...")
    logs.append("[Scraper] Arama ve canlı haber tarama süreci başlatıldı...")

    # 1. Fetch from news MCP server
    news_context = ""
    if use_news:
        try:
            logs.append(f"[Scraper] Live News MCP sunucusu (protokol) tetikleniyor: '{query}'")
            news_context = mcp_fetch_live_news(query, max_results=4)
            logs.append("[Scraper] Canlı haber akışları başarıyla çekildi.")
        except Exception as e:
            logger.error(f"Error fetching news: {e}")
            logs.append(f"[Scraper] Haber çekme hatası: {str(e)}")
    else:
        logs.append("[Scraper] Haber entegrasyonu kullanıcı tarafından devre dışı bırakıldı.")

    # 2. Fetch from web search MCP server
    web_context = ""
    if use_web:
        try:
            logs.append(f"[Scraper] Web Scraper MCP sunucusu (protokol) tetikleniyor: '{query}'")
            web_context = mcp_search_web(query, max_results=3, scrape_contents=True)
            logs.append("[Scraper] Canlı web kaynakları ve sayfa içerikleri kazındı.")
        except Exception as e:
            logger.error(f"Error searching web: {e}")
            logs.append(f"[Scraper] Web arama hatası: {str(e)}")
    else:
        logs.append("[Scraper] Web arama entegrasyonu kullanıcı tarafından devre dışı bırakıldı.")

    # 3. Index raw texts into RAG Engine
    documents = []
    
    # Parse Scraped Web Content to form documents
    if web_context:
        documents.append({
            "text": web_context,
            "source_url": "Web Search Scraper",
            "timestamp": "Live Search",
            "initial_trust_score": 0.85
        })
        
    if news_context:
        documents.append({
            "text": news_context,
            "source_url": "Live News Feeds",
            "timestamp": "Real-time",
            "initial_trust_score": 0.95
        })
        
    if documents:
        logs.append("[Scraper] Toplanan ham veriler anlamsal parçalara (chunking) ayrılıyor...")
        success = rag_engine.add_documents(documents)
        if success:
            logs.append("[Scraper] Veriler ChromaDB vektör veritabanına başarıyla indekslendi.")
        else:
            logs.append("[Scraper] RAG indeksleme hatası oluştu.")
    else:
        logs.append("[Scraper] İndekslenecek veri bulunamadı.")
        
    return {
        "logs": logs,
        "indexed": len(documents) > 0
    }

def run_cross_checker_agent(
    query: str,
    rag_engine: Any,
    temperature: float = 0.0,
    min_trust_score: float = 0.0,
    audit_feedback: str = "",
) -> Dict[str, Any]:
    """
    Cross-Checker Agent:
    Retrieves matching chunks from RAG, detects contradictions,
    and uses structured LLM to format facts and conflicts.

    Args:
        min_trust_score: Source-trust threshold applied when retrieving RAG chunks.
        audit_feedback: Feedback from a previous faithfulness audit. When present, it is
            injected into the prompt so the agent corrects unsupported claims instead of
            regenerating the same output (this is what makes the correction loop effective).
    """
    logs = []
    logger.info("Cross-Checker Agent started working...")
    logs.append("[Cross-Checker] RAG veritabanından anlamsal bağlam çekiliyor...")

    # 1. Retrieve & Rerank chunks
    chunks = rag_engine.query_and_rerank(query, top_n=3, min_trust_score=min_trust_score)
    
    if not chunks:
        logs.append("[Cross-Checker] RAG'den ilgili veri çekilemedi. Arama yetersiz olabilir.")
        return {
            "logs": logs,
            "rag_context": [],
            "report": AletheiaReport(summary="Bağlam bulunamadı.", facts=[], conflicts=[])
        }
        
    logs.append(f"[Cross-Checker] BGE Reranker ile elenmiş en kritik {len(chunks)} parça bağlam seçildi.")
    
    # 2. Build Prompt Context
    context_str = ""
    for idx, c in enumerate(chunks, 1):
        context_str += f"--- DÖKÜMAN [{idx}] ---\n"
        context_str += f"Kaynak URL: {c['metadata'].get('source_url')}\n"
        context_str += f"Zaman Damgası: {c['metadata'].get('timestamp')}\n"
        context_str += f"Güven Skoru: {c['metadata'].get('initial_trust_score')}\n"
        context_str += f"İçerik: {c['text']}\n\n"
        
    # 3. Request LLM structured analysis
    logs.append("[Cross-Checker] Kaynaklar arası sayısal, tarihsel ve mantıksal çelişki analizi yapılıyor...")
    
    system_prompt = (
        "Sen Aletheia sisteminin kıdemli Cross-Checker Ajanısın.\n"
        "Görevin, sana sunulan dökümanları incelemek, aralarındaki her türlü "
        "çelişkiyi (sayısal veriler, tarihsel uyuşmazlıklar, zıt iddialar) bulmak "
        "ve doğrulanmış somut gerçekleri (verified facts) belirlemektir.\n"
        "Kesinlikle dökümanlarda bulunmayan veya dökümanlar tarafından desteklenmeyen "
        "bilgileri doğru kabul etme (%0 Halüsinasyon hedefiyle çalış!)."
    )
    
    # If a previous audit flagged unsupported claims, steer this pass to correct them.
    correction_block = ""
    if audit_feedback:
        logs.append("[Cross-Checker] Önceki denetim geri bildirimi dikkate alınarak düzeltme yapılıyor...")
        correction_block = (
            "\n!!! ÖNEMLİ DÜZELTME TALİMATI !!!\n"
            "Bir önceki denemende ürettiğin bazı iddialar bağlam dökümanları tarafından "
            "desteklenmiyordu. Aşağıdaki denetçi geri bildirimini dikkate al; SADECE bağlam "
            "dökümanlarında doğrudan desteklenen iddiaları üret, desteklenmeyenleri tamamen çıkar:\n"
            f"--- DENETÇİ GERİ BİLDİRİMİ ---\n{audit_feedback}\n--- BİTİŞ ---\n"
        )

    user_prompt = (
        f"Kullanıcı Araştırma Sorgusu: '{query}'\n\n"
        f"Sorguyla İlgili RAG Bağlam Verileri:\n{context_str}\n"
        f"{correction_block}"
        "Lütfen bu verileri çapraz sorgula. Çelişkili durumları 'conflicts' altında, "
        "kesin ve kaynaklarca doğrulanan verileri ise 'facts' altında toplayarak "
        "AletheiaReport şemasına uygun şekilde JSON formatında dön."
    )
    
    try:
        llm = get_llm(temperature=temperature)
        
        # Check if OpenAI is used and supports structured output
        if hasattr(llm, "with_structured_output") and llm.__class__.__name__ != "FakeMessagesListChatModel":
            structured_llm = llm.with_structured_output(AletheiaReport)
            report = structured_llm.invoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ])
        else:
            # Fallback for local models/fake model
            import json
            logs.append("[Cross-Checker] Yerel model veya fallback kullanılıyor, JSON ayrıştırılıyor...")
            response = llm.invoke(f"{system_prompt}\n\n{user_prompt}")
            content = response.content.strip()
            
            # Simple JSON parse or fallback empty object
            try:
                # Find JSON bounds
                start = content.find("{")
                end = content.rfind("}") + 1
                json_data = json.loads(content[start:end])
                report = AletheiaReport(**json_data)
            except Exception as json_err:
                logger.error(f"JSON Parse error: {json_err}. raw content: {content}")
                report = AletheiaReport(
                    summary=f"Analiz tamamlandı fakat çıktı ayrıştırılamadı. Ham yanıt: {content[:100]}...",
                    facts=[],
                    conflicts=[]
                )
                
        logs.append(f"[Cross-Checker] Çapraz sorgu tamamlandı. {len(report.facts)} kesin bilgi ve {len(report.conflicts)} çelişki bulundu.")
        
        # Map chunks to list of dicts for State
        state_chunks = [{"text": c["text"], "metadata": c["metadata"]} for c in chunks]
        
        return {
            "logs": logs,
            "rag_context": state_chunks,
            "report": report
        }
        
    except Exception as e:
        logger.error(f"Cross-Checker error: {e}")
        logs.append(f"[Cross-Checker] Hata oluştu: {str(e)}")
        return {
            "logs": logs,
            "rag_context": [],
            "report": AletheiaReport(summary="Analiz sırasında hata oluştu.", facts=[], conflicts=[])
        }

def run_reporter_agent(summary: str, facts: List[VerifiedFact], conflicts: List[DetectedConflict], temperature: float = 0.0) -> Dict[str, Any]:
    """
    Reporter Agent:
    Takes verified facts and conflicts, synthesizes a high-end, structured Markdown report.
    Adds citations properly.
    """
    logs = []
    logger.info("Reporter Agent started working...")
    logs.append("[Reporter] Doğrulanmış gerçekler ve çelişkiler derleniyor...")
    
    system_prompt = (
        "Sen Aletheia sisteminin kıdemli Reporter Ajanısın.\n"
        "Görevin, doğrulanmış gerçekleri ve tespit edilen çelişkileri, son derece şık, "
        "akademik ve siber istihbarat raporu tarzında Markdown formatına dönüştürmektir.\n"
        "Her bilginin yanına mutlaka ilgili kaynak linkini [1], [2] formatında ekle.\n"
        "Raporun en üstüne şık bir doğruluk skoru paneli ve özet ekle."
    )
    
    # Structure inputs for prompt
    facts_str = ""
    for idx, f in enumerate(facts, 1):
        facts_str += f"{idx}. **Bilgi**: {f.statement}\n"
        facts_str += f"   - Güven Skoru: %{int(f.confidence_score * 100)}\n"
        facts_str += f"   - Kaynaklar: {', '.join(f.sources)}\n"
        if f.counter_claims:
            facts_str += f"   - Çürütülen İddialar: {', '.join(f.counter_claims)}\n"
        facts_str += "\n"
        
    conflicts_str = ""
    for idx, c in enumerate(conflicts, 1):
        conflicts_str += f"{idx}. **{c.title}**\n"
        conflicts_str += f"   - Uyuşmazlık Açıklaması: {c.description}\n"
        conflicts_str += f"   - Çelişen Kaynaklar: {', '.join(c.sources)}\n\n"
        
    user_prompt = (
        f"Genel Analiz Özeti:\n{summary}\n\n"
        f"Doğrulanmış Gerçekler Listesi:\n{facts_str}\n"
        f"Tespit Edilen Çelişkiler Listesi:\n{conflicts_str}\n"
        "Lütfen bu verilerden parlayan, profesyonel estetiğe sahip "
        "kapsamlı ve okuması kolay bir Doğrulama Raporu (Markdown) oluştur."
    )
    
    try:
        llm = get_llm(temperature=temperature)
        response = llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ])
        
        final_report = response.content
        logs.append("[Reporter] Doğrulama raporu başarıyla sentezlendi ve biçimlendirildi.")
        
        return {
            "logs": logs,
            "final_report": final_report
        }
    except Exception as e:
        logger.error(f"Reporter failed: {e}")
        logs.append(f"[Reporter] Hata oluştu: {str(e)}")
        
        # Simple fallback report layout
        fallback_report = (
            f"# Aletheia Doğrulama Raporu\n\n"
            f"## Özet\n{summary}\n\n"
            f"## Doğrulanmış Gerçekler\n"
            + "\n".join([f"- {f.statement} [Güven Skoru: %{int(f.confidence_score*100)}]" for f in facts])
        )
        return {
            "logs": logs,
            "final_report": fallback_report
        }
