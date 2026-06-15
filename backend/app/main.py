#!/usr/bin/env python3
"""
Aletheia FastAPI Gateway

Description:
    Exposes a Server-Sent Events (SSE) streaming API endpoint to execute the 
    LangGraph verification workflow asynchronously and push real-time agent logs, 
    checkpoints, and final reports to the Streamlit UI.
"""

import os
import json
import uuid
import logging
import asyncio
from datetime import datetime, timezone
from fastapi import FastAPI, Query, status
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.app.graph import aletheia_graph

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("AletheiaAPI")

# Initialize FastAPI App
app = FastAPI(
    title="Aletheia Verification & Analysis Engine API",
    description="Multi-Agent MCP & Advanced RAG Verification backend powered by LangGraph.",
    version="1.0.0"
)

# Configure CORS Middleware for cross-origin frontend requests.
# NOTE: a wildcard origin is incompatible with credentialed requests per the CORS
# spec, so allow_credentials must stay False while allow_origins is "*".
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 1. Pydantic API Models
# ==========================================

class VerificationRequest(BaseModel):
    query: str = Field(..., description="Araştırılmak istenen canlı konu veya sorgu")
    temperature: float = Field(default=0.0, ge=0.0, le=1.0, description="LLM üretkenlik sıcaklığı (0.0=katı, 1.0=yaratıcı)")
    source_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Kaynak güvenilirlik eşik değeri")
    use_web: bool = Field(default=True, description="Web arama MCP entegrasyonunu etkinleştir")
    use_news: bool = Field(default=True, description="Canlı haber MCP entegrasyonunu etkinleştir")

# ==========================================
# 2. SSE Event Stream Generator
# ==========================================

async def event_stream_generator(
    query: str,
    temperature: float,
    source_threshold: float = 0.0,
    use_web: bool = True,
    use_news: bool = True,
):
    """
    Asynchronously executes the LangGraph workflow step-by-step
    and yields Server-Sent Events (SSE) to the client.
    """
    session_id = uuid.uuid4().hex
    logger.info(f"Starting SSE event stream (session={session_id}) for query: '{query}' with temp={temperature}")

    # Initialize state inputs
    inputs = {
        "query": query,
        "temperature": temperature,
        "source_threshold": source_threshold,
        "faithfulness_threshold": 0.85,
        "use_web": use_web,
        "use_news": use_news,
        "session_id": session_id,
        "rag_context": [],
        "detected_conflicts": [],
        "verified_facts": [],
        "final_report": "",
        "hallucination_score": 0.0,
        "logs": [],
        "iterations": 0,
        "audit_feedback": "",
    }
    
    sent_logs_count = 0
    
    try:
        # Run LangGraph workflow asynchronously in streaming mode
        async for event in aletheia_graph.astream(inputs, stream_mode="updates"):
            # Ensure cooperative multitasking
            await asyncio.sleep(0.01)
            
            # event is a dictionary mapping: node_name -> state_updates
            for node_name, updates in event.items():
                logger.info(f"Node completed: {node_name}")
                
                # 1. Extract new logs and yield as 'event: log'
                logs = updates.get("logs", [])
                if len(logs) > sent_logs_count:
                    new_logs = logs[sent_logs_count:]
                    for log_msg in new_logs:
                        data = {"message": log_msg}
                        yield f"event: log\ndata: {json.dumps(data)}\n\n"
                    sent_logs_count = len(logs)
                
                # 2. Compile metrics/state and yield as 'event: checkpoint'
                checkpoint_data = {
                    "active_node": node_name,
                    "verified_facts_count": len(updates.get("verified_facts", [])),
                    "detected_conflicts_count": len(updates.get("detected_conflicts", [])),
                    "hallucination_score": updates.get("hallucination_score", 0.0),
                    "iterations": updates.get("iterations", 0)
                }
                yield f"event: checkpoint\ndata: {json.dumps(checkpoint_data)}\n\n"
                
                # 3. If final report node finishes, compile and yield 'event: final_result'
                if node_name == "reporter" and "final_report" in updates:
                    final_data = {
                        "final_report": updates["final_report"],
                        "verified_facts": updates.get("verified_facts", []),
                        "detected_conflicts": updates.get("detected_conflicts", [])
                    }
                    yield f"event: final_result\ndata: {json.dumps(final_data)}\n\n"
                    
    except Exception as e:
        logger.error(f"Error encountered during LangGraph execution stream: {e}")
        error_data = {"message": f"Doğrulama motoru çalışırken bir iç hata oluştu: {str(e)}"}
        yield f"event: error\ndata: {json.dumps(error_data)}\n\n"

# ==========================================
# 3. Endpoint Routings
# ==========================================

@app.get("/api/verify")
async def verify_stream(
    query: str = Query(..., description="Doğrulamak istediğiniz sorgu"),
    temperature: float = Query(default=0.0, ge=0.0, le=1.0, description="Yapay zeka sıcaklık parametresi"),
    source_threshold: float = Query(default=0.0, ge=0.0, le=1.0, description="Kaynak güvenilirlik eşik değeri"),
    use_web: bool = Query(default=True, description="Web arama MCP entegrasyonu"),
    use_news: bool = Query(default=True, description="Canlı haber MCP entegrasyonu"),
):
    """
    GET endpoint returning a Server-Sent Events (SSE) stream of
    the Aletheia agent verification process.
    """
    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no"  # Critical for Nginx reverse-proxies to prevent buffering
    }
    return StreamingResponse(
        event_stream_generator(query, temperature, source_threshold, use_web, use_news),
        headers=headers,
        media_type="text/event-stream"
    )

@app.get("/health")
async def health_check():
    """
    Simple API health check endpoint.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    # Start FastAPI server on port 8999 (matches run_local.sh and the frontend client).
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8999, reload=True)
