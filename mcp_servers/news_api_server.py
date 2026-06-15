#!/usr/bin/env python3
"""
Aletheia MCP News API Server
Author: Senior AI Architect
Description:
    Model Context Protocol (MCP) server for fetching real-time news.
    Queries NewsAPI if key is available, or parses trusted global news RSS feeds 
    (BBC, NYT, CNBC) with keyword matching as a zero-key fallback.
"""

import os
import logging
import requests
# pyrefly: ignore [missing-import]
import feedparser
from typing import List, Dict, Any, Optional
from datetime import datetime
# pyrefly: ignore [missing-import]
from mcp.server.fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("AletheiaNewsServer")

# Initialize FastMCP Server
mcp = FastMCP("Aletheia News Server")

# Trusted RSS Feeds for Zero-Key Fallback
TRUSTED_RSS_FEEDS = {
    "BBC World News": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "NYT World News": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "CNBC Business/Finance": "https://search.cnbc.com/rs/search/all/view.rss",
    "Reuters Agency": "https://www.reutersagency.com/feed/"
}

def query_news_api(query: str, max_results: int) -> Optional[List[Dict[str, Any]]]:
    """
    Queries NewsAPI for articles matching the query.
    """
    news_key = os.environ.get("NEWS_API_KEY")
    if not news_key:
        return None
        
    try:
        logger.info("Querying NewsAPI...")
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "sortBy": "publishedAt",
            "pageSize": max_results,
            "apiKey": news_key,
            "language": "en"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") != "ok":
            logger.error(f"NewsAPI error status: {data.get('message')}")
            return None
            
        articles = []
        for art in data.get("articles", []):
            articles.append({
                "title": art.get("title", ""),
                "source_name": art.get("source", {}).get("name", "Unknown Source"),
                "author": art.get("author") or "N/A",
                "published_at": art.get("publishedAt", ""),
                "description": art.get("description", ""),
                "content": art.get("content", ""),
                "url": art.get("url", ""),
                "source_type": "NewsAPI"
            })
        return articles
        
    except Exception as e:
        logger.error(f"NewsAPI query failed: {e}")
        return None

def fetch_rss_fallback_news(query: str, max_results: int) -> List[Dict[str, Any]]:
    """
    Parses global RSS feeds and filters entries matching the query keywords.
    """
    logger.info("Executing RSS Fallback News Parser...")
    query_words = [w.lower() for w in query.split() if len(w) > 2]
    all_articles = []
    
    for feed_name, feed_url in TRUSTED_RSS_FEEDS.items():
        try:
            logger.info(f"Parsing feed: {feed_name}")
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries:
                title = entry.get("title", "")
                summary = entry.get("summary", "") or entry.get("description", "")
                link = entry.get("link", "")
                pub_date = entry.get("published", "") or entry.get("updated", "")
                
                # Check for query match
                text_to_search = (title + " " + summary).lower()
                matches = False
                
                if not query_words:
                    # If empty query, matches everything
                    matches = True
                else:
                    # Matches if at least one keyword is present
                    matches = any(word in text_to_search for word in query_words)
                    
                if matches:
                    all_articles.append({
                        "title": title,
                        "source_name": feed_name,
                        "author": "Associated Press / Reuter / Staff",
                        "published_at": pub_date,
                        "description": summary,
                        "content": summary, # RSS typically only has summary
                        "url": link,
                        "source_type": "RSS Feed"
                    })
        except Exception as e:
            logger.warning(f"Error parsing feed '{feed_name}': {e}")
            
    # Sort by publication date or limit
    # (Since RSS formats differ, we'll just keep the first N matches)
    return all_articles[:max_results]

@mcp.tool()
def fetch_live_news(query: str, max_results: int = 5) -> str:
    """
    Fetches real-time news articles from NewsAPI or trusted global RSS feeds.
    
    Args:
        query: Keywords to filter news articles.
        max_results: Maximum number of articles to return.
        
    Returns:
        A formatted Markdown string containing live news articles and their details.
    """
    logger.info(f"Received news fetch request for query: '{query}'")
    
    # 1. Try NewsAPI if key is available
    articles = query_news_api(query, max_results)
    
    # 2. Fall back to RSS Feeds parsing
    if not articles:
        articles = fetch_rss_fallback_news(query, max_results)
        
    if not articles:
        return f"### No live news articles found for search term: '{query}'\nVerify your query or check back later."
        
    # 3. Format output
    output = [f"# Live News Updates for: *{query}*", ""]
    
    for i, art in enumerate(articles, 1):
        title = art['title']
        source = art['source_name']
        author = art['author']
        pub_date = art['published_at']
        url = art['url']
        desc = art['description']
        content = art['content']
        src_type = art['source_type']
        
        output.append(f"### [{i}] {title}")
        output.append(f"- **Source**: {source} ({src_type})")
        output.append(f"- **Published At**: {pub_date}")
        output.append(f"- **Author**: {author}")
        output.append(f"- **Link**: {url}")
        output.append(f"- **Summary**: {desc}")
        if content and content != desc:
            # Clean HTML or truncate content
            clean_content = content[:300] + "..." if len(content) > 300 else content
            output.append(f"- **Snippet**: {clean_content}")
            
        output.append("\n" + "="*40 + "\n")
        
    return "\n".join(output)

if __name__ == "__main__":
    # Standard MCP server run
    mcp.run()
