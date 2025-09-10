"""English prompts for Sayu"""

from typing import List


def main_analysis(conversations: str, staged_files: List[str], diff_stats: str, process_analysis: str) -> str:
    """Main LLM analysis prompt in English"""
    files_str = ', '.join(staged_files[:10])  # Limit for better readability
    if len(staged_files) > 10:
        files_str += f" (+{len(staged_files)-10} more)"
    
    return f"""Analyze this commit to provide effective context for future development.

## 🗂 Changed Files:
{files_str}

## 📊 Change Statistics:
{diff_stats}

## 💬 Related Conversations:
{conversations[:3000]}

## 📈 Development Process Analysis:
{process_analysis}

**Core Principles:**
- Focus on capturing context that would help understand this commit in the future
- Include both successful and failed attempts to show the full development process
- Document the "why" behind changes, not just the "what"
- Be specific about technical details and implementation choices

Return JSON with these three key aspects:

{{
  "what_changed": "Comprehensive list of all changes made in this commit. Include specific files, functions, classes, methods, logic modifications, and their exact locations. Mention added/removed/modified code sections. Be detailed and technically precise.",
  
  "conversation_flow": "The complete development journey from the conversations. Start with the initial request/problem, then describe how the discussion evolved - what approaches were tried first, what didn't work and why, what alternatives were considered, what challenges arose and how they were resolved. Include key decision points and reasoning behind technical choices.",
  
  "intent": "The core purpose and motivation behind these changes. If explicitly stated in conversations, quote the relevant parts. Otherwise, infer from the context. Why was this work necessary? What specific problem does it solve? What goal does it achieve? How does it improve the codebase?"
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
