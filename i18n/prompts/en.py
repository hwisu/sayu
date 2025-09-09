"""English prompts for Sayu"""

from typing import List


def main_analysis(conversations: str, staged_files: List[str], diff_stats: str, process_analysis: str) -> str:
    """Main LLM analysis prompt in English"""
    files_str = ', '.join(staged_files)
    
    return f"""Analyze this commit to provide effective context for future development.

## 🗂 Changed Files:
{files_str}

## 📊 Change Statistics:
{diff_stats}

## 💬 Related Conversations:
{conversations}

## 📈 Conversation Pattern Analysis:
{process_analysis}

**Core Principles:**
- Focus on capturing context that would help understand this commit in the future
- Include both successful and failed attempts to show the full development process
- Document the "why" behind changes, not just the "what"

Return JSON with these three key aspects:

{{
  "what_changed": "Comprehensive list of all changes made in this commit. Include specific files, functions, logic modifications, and their locations. Be detailed and precise.",
  
  "conversation_flow": "The development journey from the conversations. How did the discussion evolve? What approaches were tried? What challenges arose and how were they addressed? Include key decision points.",
  
  "intent": "The purpose behind these changes. If explicitly stated in conversations, quote it. Otherwise, infer from the context. Why was this work necessary? What problem does it solve?"
}}

JSON response:"""


def simplified_analysis(conversations: str, staged_files: List[str], diff_stats: str) -> str:
    """Simplified retry prompt in English"""
    files_str = ', '.join(staged_files)
    
    return f"""Provide a concise commit analysis for context.

## 💬 Conversations:
{conversations}

## 📁 Files:
{files_str}

## 📊 Changes:
{diff_stats}

Return a brief JSON summary:

{{
  "what_changed": "Key modifications made (files, functions, logic)",
  "conversation_flow": "How the development discussion progressed",
  "intent": "Purpose of changes (explicit or inferred)"
}}

JSON response:"""


# Export dictionary for compatibility
en_prompts = {
    'main_analysis': main_analysis,
    'simplified_analysis': simplified_analysis
}
