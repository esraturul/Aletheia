# Aletheia

Aletheia is an AI-powered fact-checking and verification system. It utilizes a LangGraph-based multi-agent architecture and RAG (Retrieval-Augmented Generation) to extract data from external sources and generate consensus reports.

## Features

*   **Agentic Architecture:** Uses LangGraph to verify claims, detect hallucinations, and prevent them through an iterative decision-making process.
*   **RAG & Vector Search:** Performs vector search using session-based isolated ChromaDB collections and maximizes relevance through Cross-Encoder re-ranking.
*   **Real-Time Streaming (SSE):** Agent logs and results are streamed in real-time to the interface using Server-Sent Events (SSE).
*   **MCP Integrations:** Integrated with FastMCP servers for fetching live News APIs (NewsAPI/RSS) and Web Scraping.

## Architecture

*   **Backend (Port 8999):** FastAPI server that runs the LangGraph workflow and RAG engine.
*   **Frontend (Port 8555):** Streamlit interface for user interaction and data visualization.
*   **MCP Servers:** Independent modules used to fetch data from the outside world.

## Setup & Execution

### 1. Requirements
*   Python 3.9 or higher

### 2. Installation
Create a virtual environment and install the required dependencies:

```bash
python3 -m venv venv
source venv/bin/activate

pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt
pip install -r mcp_servers/requirements.txt
```

### 3. Environment Variables
Create an `.env` file in the root directory and add your API keys:

```env
NEWS_API_KEY=your_news_api_key_here
```

### 4. Running the Application
Start the project using the provided initialization script:

```bash
chmod +x run_local.sh
./run_local.sh
```

Once the project is running, you can access the interface by navigating to **http://localhost:8555** in your browser.
