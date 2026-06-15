#!/usr/bin/env python3
"""
Aletheia MCP Client Bridge

Description:
    Connects to the Aletheia MCP servers (web scraper + news) over the real
    Model Context Protocol (stdio transport), lists/invokes their tools, and
    returns the textual results.

    This is what makes "MCP" in Aletheia an actual protocol integration rather
    than an in-process function import. If a server cannot be spawned or the
    protocol call fails, the bridge degrades gracefully to a direct in-process
    call of the same tool function so the verification pipeline never hard-fails.
"""

import os
import sys
import asyncio
import logging
import threading
from typing import Any, Dict, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger("AletheiaMCPClient")

# Absolute paths to the MCP server entry points
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_SCRAPER_SERVER = os.path.join(_THIS_DIR, "web_scraper_server.py")
NEWS_API_SERVER = os.path.join(_THIS_DIR, "news_api_server.py")


def _run_async(coro) -> Any:
    """
    Runs an async coroutine to completion from synchronous code, even when called
    from inside a thread that may or may not already own an event loop. We always
    execute on a dedicated thread with a fresh loop to avoid 'event loop already
    running' conflicts with the FastAPI/uvicorn host loop.
    """
    result: Dict[str, Any] = {}

    def _worker():
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            result["value"] = loop.run_until_complete(coro)
        except Exception as e:  # noqa: BLE001 - propagate to caller
            result["error"] = e
        finally:
            loop.close()

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join()

    if "error" in result:
        raise result["error"]
    return result.get("value")


async def _call_tool_async(server_path: str, tool_name: str, arguments: Dict[str, Any]) -> str:
    """
    Spawns the given MCP server over stdio, performs the protocol handshake, invokes
    the named tool with the supplied arguments, and returns the concatenated text output.
    """
    # Ensure the server subprocess can import the project packages
    env = dict(os.environ)
    project_root = os.path.abspath(os.path.join(_THIS_DIR, ".."))
    env["PYTHONPATH"] = project_root + os.pathsep + env.get("PYTHONPATH", "")

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-u", server_path],
        env=env,
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            logger.info(f"[MCP] Connected to server '{os.path.basename(server_path)}', calling tool '{tool_name}'.")
            result = await session.call_tool(tool_name, arguments=arguments)

            # Concatenate any text content blocks returned by the tool
            parts = []
            for block in (result.content or []):
                text = getattr(block, "text", None)
                if text:
                    parts.append(text)
            return "\n".join(parts)


def call_mcp_tool(server_path: str, tool_name: str, arguments: Dict[str, Any]) -> Optional[str]:
    """
    Synchronous wrapper around an MCP tool call. Returns the tool's text output,
    or None if the protocol invocation failed (caller may then fall back).
    """
    try:
        return _run_async(_call_tool_async(server_path, tool_name, arguments))
    except Exception as e:  # noqa: BLE001
        logger.error(f"[MCP] Protocol call to '{tool_name}' failed: {e}")
        return None


# ==========================================
# High-level tool helpers (with direct fallback)
# ==========================================

def mcp_search_web(query: str, max_results: int = 5, scrape_contents: bool = True) -> str:
    """
    Calls the web scraper MCP server's `search_web` tool over the protocol.
    Falls back to a direct in-process call if the protocol invocation fails.
    """
    out = call_mcp_tool(
        WEB_SCRAPER_SERVER,
        "search_web",
        {"query": query, "max_results": max_results, "scrape_contents": scrape_contents},
    )
    if out is not None:
        return out

    logger.warning("[MCP] Falling back to direct in-process search_web call.")
    from mcp_servers.web_scraper_server import search_web
    return search_web(query, max_results=max_results, scrape_contents=scrape_contents)


def mcp_fetch_live_news(query: str, max_results: int = 5) -> str:
    """
    Calls the news MCP server's `fetch_live_news` tool over the protocol.
    Falls back to a direct in-process call if the protocol invocation fails.
    """
    out = call_mcp_tool(
        NEWS_API_SERVER,
        "fetch_live_news",
        {"query": query, "max_results": max_results},
    )
    if out is not None:
        return out

    logger.warning("[MCP] Falling back to direct in-process fetch_live_news call.")
    from mcp_servers.news_api_server import fetch_live_news
    return fetch_live_news(query, max_results=max_results)
