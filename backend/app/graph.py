#!/usr/bin/env python3
"""
Aletheia LangGraph Orchestrator
Author: Senior AI Architect
Description:
    Defines the stateful multi-agent LangGraph workflow, connects nodes,
    and implements conditional routing loops based on faithfulness guardrail scores.
"""

import logging
from typing import List, Dict, Any, TypedDict
from langgraph.graph import StateGraph, END

from backend.app.rag_engine import AletheiaRAGEngine
from backend.app.agents import (
    run_scraper_agent,
    run_cross_checker_agent,
    run_reporter_agent,
    VerifiedFact,
    DetectedConflict
)
from backend.app.guardrails import evaluate_faithfulness

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("AletheiaGraph")

# ==========================================
# 1. State Definition
# ==========================================

class AletheiaState(TypedDict):
    query: str
    rag_context: List[Dict[str, Any]]
    detected_conflicts: List[Dict[str, Any]]
    verified_facts: List[Dict[str, Any]]
    final_report: str
    hallucination_score: float
    logs: List[str]
    iterations: int
    temperature: float

# ==========================================
# 2. Global RAG Engine Instance
# ==========================================

rag_engine = AletheiaRAGEngine()

# ==========================================
# 3. Agent Nodes Definition
# ==========================================

def scraper_node(state: AletheiaState) -> Dict[str, Any]:
    """
    Executes the Scraper Agent tool calls and indices content in RAG.
    """
    logger.info("Executing Scraper Node...")
    query = state.get("query", "")
    
    # Reset or initialize state parameters
    current_logs = state.get("logs", []) or []
    current_logs.append("--- [SİSTEM BAŞLANGICI: ALETHEIA VERIFICATION MOTORU] ---")
    
    # Clear the temporary DB collection for the new session to keep it fresh
    rag_engine.clear_database()
    
    # Run Scraper Agent
    res = run_scraper_agent(query, rag_engine)
    
    # Update logs list
    for log_item in res["logs"]:
        current_logs.append(log_item)
        
    return {
        "logs": current_logs,
        "iterations": 0, # Initialize loop counter
        "rag_context": [],
        "detected_conflicts": [],
        "verified_facts": [],
        "final_report": "",
        "hallucination_score": 0.0
    }

def cross_checker_node(state: AletheiaState) -> Dict[str, Any]:
    """
    Retrieves information from RAG, detects contradictions, 
    and extracts structured facts/conflicts.
    """
    logger.info("Executing Cross-Checker Node...")
    query = state.get("query", "")
    temp = state.get("temperature", 0.0)
    current_logs = state.get("logs", []) or []
    current_iters = state.get("iterations", 0)
    
    if current_iters > 0:
        current_logs.append(f"[Sistem] Halüsinasyon düzeltme döngüsü tetiklendi! Iterasyon: {current_iters}")
        
    # Run Cross-Checker Agent
    res = run_cross_checker_agent(query, rag_engine, temperature=temp)
    
    for log_item in res["logs"]:
        current_logs.append(log_item)
        
    # Extract structural components of report
    report = res["report"]
    
    # Map Pydantic lists to standard dict lists for serialization
    facts_list = []
    for f in report.facts:
        facts_list.append({
            "statement": f.statement,
            "confidence_score": f.confidence_score,
            "sources": f.sources,
            "counter_claims": f.counter_claims
        })
        
    conflicts_list = []
    for c in report.conflicts:
        conflicts_list.append({
            "title": c.title,
            "description": c.description,
            "sources": c.sources
        })
        
    return {
        "logs": current_logs,
        "rag_context": res["rag_context"],
        "verified_facts": facts_list,
        "detected_conflicts": conflicts_list,
        "iterations": current_iters + 1
    }

def fact_checker_node(state: AletheiaState) -> Dict[str, Any]:
    """
    Audits the generated claims against RAG context.
    Updates hallucination score and logs justification.
    """
    logger.info("Executing Fact-Checker Node...")
    current_logs = state.get("logs", []) or []
    
    # Map dictionaries back to Pydantic objects for evaluation
    facts = []
    for f in state.get("verified_facts", []):
        facts.append(VerifiedFact(
            statement=f["statement"],
            confidence_score=f["confidence_score"],
            sources=f["sources"],
            counter_claims=f.get("counter_claims", [])
        ))
        
    rag_context = state.get("rag_context", [])
    
    # Run Anti-Hallucination Guardrail Check
    current_logs.append("[Fact-Checker] Anti-halüsinasyon ve sadakat (faithfulness) denetimi yapılıyor...")
    eval_res = evaluate_faithfulness(facts, rag_context)
    
    faith_score = eval_res["faithfulness_score"]
    reasoning = eval_res["reasoning"]
    
    current_logs.append(f"[Fact-Checker] Sadakat Skoru: %{int(faith_score * 100)}")
    current_logs.append(f"[Fact-Checker] Denetçi Gerekçesi: {reasoning}")
    
    hallucination_score = float(1.0 - faith_score)
    
    return {
        "logs": current_logs,
        "hallucination_score": hallucination_score
    }

def reporter_node(state: AletheiaState) -> Dict[str, Any]:
    """
    Synthesizes the finalized, gorgeous siber-intelligence Markdown verification report.
    """
    logger.info("Executing Reporter Node...")
    temp = state.get("temperature", 0.0)
    current_logs = state.get("logs", []) or []
    
    # Re-structure summary context
    facts = []
    for f in state.get("verified_facts", []):
        facts.append(VerifiedFact(
            statement=f["statement"],
            confidence_score=f["confidence_score"],
            sources=f["sources"],
            counter_claims=f.get("counter_claims", [])
        ))
        
    conflicts = []
    for c in state.get("detected_conflicts", []):
        conflicts.append(DetectedConflict(
            title=c["title"],
            description=c["description"],
            sources=c["sources"]
        ))
        
    summary = f"Aletheia doğrulamayı başarıyla tamamladı. Güven skoru yüksek seviyede."
    
    # Run Reporter Agent
    res = run_reporter_agent(summary, facts, conflicts, temperature=temp)
    
    for log_item in res["logs"]:
        current_logs.append(log_item)
        
    current_logs.append("--- [ALETHEIA DOĞRULAMA TAMAMLANDI - RAPOR HAZIR] ---")
    
    return {
        "logs": current_logs,
        "final_report": res["final_report"]
    }

# ==========================================
# 4. Conditional Loop Routing
# ==========================================

def check_hallucinations(state: AletheiaState) -> str:
    """
    Determines whether the system should loop back to fix hallucinations
    or advance to the reporter node. Capped at maximum 3 attempts.
    """
    iterations = state.get("iterations", 0)
    hallucination_score = state.get("hallucination_score", 0.0)
    faithfulness_score = 1.0 - hallucination_score
    
    logger.info(f"Conditional Routing - Iteration: {iterations}, Faithfulness: {faithfulness_score}")
    
    # Max iterations exceeded. Exit loop to prevent lockup.
    if iterations >= 3:
        logger.warning("Max iterations limit reached! Routing directly to report synthesis.")
        state.get("logs", []).append("[Sistem] Maksimum denetim limitine ulaşıldı, rapor sentezleniyor...")
        return "reporter"
        
    # Check if faithfulness matches the 0.85 threshold
    if faithfulness_score < 0.85:
        logger.warning(f"Faithfulness score ({faithfulness_score}) < 0.85. HALLUCINATION DETECTED! Looping back.")
        state.get("logs", []).append(
            f"[Sistem] UYARI: Halüsinasyon/Bağlam Dışı İddia Tespit Edildi (Sadakat Skoru: %{int(faithfulness_score*100)} < %85)! "
            "Ajanlar düzeltme ve yeniden sorgulama yapmak üzere yönlendiriliyor..."
        )
        return "cross_checker"
    else:
        logger.info(f"Faithfulness score ({faithfulness_score}) >= 0.85. Verification passed. Routing to reporter.")
        state.get("logs", []).append("[Sistem] BİLGİ: Sadakat denetimi başarıyla tamamlandı. Rapor yazımına geçiliyor...")
        return "reporter"

# ==========================================
# 5. LangGraph Workflow Compilation
# ==========================================

workflow = StateGraph(AletheiaState)

# Add Nodes to Graph
workflow.add_node("scraper", scraper_node)
workflow.add_node("cross_checker", cross_checker_node)
workflow.add_node("fact_checker", fact_checker_node)
workflow.add_node("reporter", reporter_node)

# Set Entry Node
workflow.set_entry_point("scraper")

# Define Static Transitions
workflow.add_edge("scraper", "cross_checker")
workflow.add_edge("cross_checker", "fact_checker")

# Define Conditional Transition
workflow.add_conditional_edges(
    "fact_checker",
    check_hallucinations,
    {
        "cross_checker": "cross_checker",
        "reporter": "reporter"
    }
)

# Connect Reporter to END
workflow.add_edge("reporter", END)

# Compile LangGraph app
aletheia_graph = workflow.compile()
