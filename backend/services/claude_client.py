"""
backend/services/claude_client.py
====================================
Legacy alias module redirecting to llm_client.py (Groq primary + Gemini fallback).
"""

from .llm_client import stream_analysis

__all__ = ["stream_analysis"]
