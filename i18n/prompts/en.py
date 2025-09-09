"""English prompts for Sayu"""

from typing import List


def main_analysis(conversations: str, staged_files: List[str], diff_stats: str, process_analysis: str) -> str:
    """Main LLM analysis prompt in English"""
    files_str = ', '.join(staged_files)
    
    return f"""Analyze this commit to capture the complete development trail.

## 🗂 Changed Files:
{files_str}

## 📊 Change Statistics:
{diff_stats}

## 💬 Related Conversations:
{conversations}

## 📈 Conversation Pattern Analysis:
{process_analysis}

**IMPORTANT: Return only valid JSON. No markdown, no code blocks, no explanations. Only JSON output.**

**CRITICAL INSTRUCTIONS FOR FULL TRAIL COVERAGE:**
1. Capture the complete journey, not just the final result
2. Include ALL attempted approaches, even if they didn't work
3. Document key decision points and rationale
4. Preserve important error messages or debugging insights
5. Note any external references, documentation, or resources consulted
6. Include any performance considerations or trade-offs discussed

Response format (valid JSON only):
{{
  "intent": "The initial problem/goal and how understanding evolved during development. Include any pivots or refinements in approach",
  "changes": "Complete list of modifications including: files changed, specific methods/functions affected, configuration changes, test additions, and any refactoring done. Be specific about WHAT changed and WHERE", 
  "context": "Full development trail including: initial approach, challenges encountered, solutions tried, debugging process, key insights discovered, decisions made and why, any remaining considerations or follow-up items. This should tell the complete story of how this code came to be"
}}

JSON response:"""


def simplified_analysis(conversations: str, staged_files: List[str], diff_stats: str) -> str:
    """Simplified retry prompt in English"""
    files_str = ', '.join(staged_files)
    
    return f"""Analyze this commit focusing on the development flow:

## 💬 Conversations:
{conversations}

## 📁 Files:
{files_str}

## 📊 Changes:
{diff_stats}

**IMPORTANT: Return only valid JSON. No markdown or explanations. JSON only.**

**FOCUS: Capture the development flow concisely but completely**

Response format (valid JSON only):
{{
  "intent": "Initial problem → final goal (show evolution)",
  "changes": "File changes with specific locations and modifications",
  "context": "Development flow: start → challenges → solutions → outcome"
}}

JSON response:"""


# Export dictionary for compatibility
en_prompts = {
    'main_analysis': main_analysis,
    'simplified_analysis': simplified_analysis
}
