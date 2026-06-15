#!/usr/bin/env python3
"""
Aletheia MCP Web Scraper Server

Description:
    Model Context Protocol (MCP) server for searching and scraping the web.
    Integrates with Tavily and Serper, and provides a robust zero-key fallback using
    DuckDuckGo search and BeautifulSoup web scraping.
"""

import os
import logging
import requests
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("AletheiaWebScraper")

# Initialize FastMCP Server
mcp = FastMCP("Aletheia Web Scraper")

# Constants
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def scrape_url(url: str, timeout: int = 5) -> str:
    """
    Scrapes a web page and returns its cleaned text content.
    """
    try:
        headers = {"User-Agent": DEFAULT_USER_AGENT}
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Remove non-content elements
        for element in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            element.decompose()
            
        # Extract paragraph texts
        paragraphs = [p.get_text().strip() for p in soup.find_all("p") if len(p.get_text().strip()) > 30]
        
        if not paragraphs:
            # Fallback to general text if no paragraphs are found
            text = soup.get_text(separator="\n")
            lines = [line.strip() for line in text.splitlines() if len(line.strip()) > 30]
            paragraphs = lines[:10]  # Get first 10 dense lines
            
        cleaned_text = "\n\n".join(paragraphs[:8]) # Keep a reasonable size to prevent token blowup
        return cleaned_text if cleaned_text else "No extractable text content found."
        
    except Exception as e:
        logger.warning(f"Error scraping URL {url}: {e}")
        return f"Failed to scrape content due to error: {str(e)}"

def run_tavily_search(query: str, max_results: int) -> Optional[List[Dict[str, Any]]]:
    """
    Executes search using Tavily API.
    """
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if not tavily_key:
        return None
        
    try:
        logger.info("Using Tavily Search API...")
        from tavily import TavilyClient
        client = TavilyClient(api_key=tavily_key)
        response = client.search(query=query, max_results=max_results, include_raw_content=False)
        
        results = []
        for res in response.get("results", []):
            results.append({
                "title": res.get("title", ""),
                "url": res.get("url", ""),
                "snippet": res.get("content", ""),
                "source": "tavily"
            })
        return results
    except Exception as e:
        logger.error(f"Tavily Search failed: {e}")
        return None

def run_serper_search(query: str, max_results: int) -> Optional[List[Dict[str, Any]]]:
    """
    Executes search using Serper (Google Search) API.
    """
    serper_key = os.environ.get("SERPER_API_KEY")
    if not serper_key:
        return None
        
    try:
        logger.info("Using Serper Search API...")
        url = "https://google.serper.dev/search"
        payload = {"q": query, "num": max_results}
        headers = {
            'X-API-KEY': serper_key,
            'Content-Type': 'application/json'
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data.get("organic", [])[:max_results]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source": "serper"
            })
        return results
    except Exception as e:
        logger.error(f"Serper Search failed: {e}")
        return None

def run_ddg_fallback_search(query: str, max_results: int) -> List[Dict[str, Any]]:
    """
    Executes zero-key fallback search using DuckDuckGo.
    """
    logger.info("Using DuckDuckGo Fallback Search...")
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            ddg_results = list(ddgs.text(query, max_results=max_results))
            for res in ddg_results:
                results.append({
                    "title": res.get("title", ""),
                    "url": res.get("href", ""),
                    "snippet": res.get("body", ""),
                    "source": "duckduckgo"
                })
        return results
    except Exception as e:
        logger.error(f"DuckDuckGo search failed: {e}")
        return []

@mcp.tool()
def search_web(query: str, max_results: int = 5, scrape_contents: bool = True) -> str:
    """
    Searches the web for the given query and scrapes the content of matching pages.
    
    Args:
        query: The search string to query the web.
        max_results: The maximum number of search results to return.
        scrape_contents: If True, fetches and extracts the text content of the target URLs.
        
    Returns:
        A structured Markdown string with search results and detailed page text.
    """
    logger.info(f"Received search request for query: '{query}'")
    
    # 1. Attempt API searches first
    results = run_tavily_search(query, max_results)
    if not results:
        results = run_serper_search(query, max_results)
        
    # 2. Fall back to DuckDuckGo search
    if not results:
        results = run_ddg_fallback_search(query, max_results)
        
    if not results:
        return f"### No results found for query: '{query}'\nVerify your network connection or API credentials."

    # 3. Compile output and scrape pages if required
    output = [f"# Search Results for: *{query}*", ""]
    
    for i, res in enumerate(results, 1):
        title = res['title']
        url = res['url']
        snippet = res['snippet']
        source = res['source']
        
        output.append(f"### [{i}] {title}")
        output.append(f"- **URL**: {url}")
        output.append(f"- **Source**: {source}")
        output.append(f"- **Summary/Snippet**: {snippet}")
        
        if scrape_contents:
            output.append("- **Scraped Content Details**:")
            logger.info(f"Scraping [{i}/{len(results)}]: {url}")
            scraped_content = scrape_url(url)
            # Indent content for clean Markdown nesting
            indented_content = "\n".join([f"  > {line}" for line in scraped_content.splitlines()])
            output.append(indented_content)
            
        output.append("\n" + "-"*40 + "\n")
        
    return "\n".join(output)

if __name__ == "__main__":
    # Standard MCP server run
    mcp.run()
