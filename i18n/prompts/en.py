"""English prompts for Sayu"""

from typing import List


def main_analysis(conversations: str, staged_files: List[str], diff_stats: str, process_analysis: str) -> str:
    """Main LLM analysis prompt in English"""
    files_str = ', '.join(staged_files)
    
    return f"""Analyze this commit to generate concise context.

## 🗂 Changed Files:
{files_str}

## 📊 Change Statistics:
{diff_stats}

## 💬 Related Conversations:
{conversations}

## 📈 Conversation Pattern Analysis:
{process_analysis}

Please respond only in the following JSON format (use concise and essential language):
{{
  "intent": "Specific problem or goal this commit aimed to solve (based on changed files and conversation content)",
  "changes": "Concrete modifications in changed files and implementation methods (include file names and changes)",
  "context": "Key findings, problem-solving process, and notable points from development (concisely)"
}}"""


def simplified_analysis(conversations: str, staged_files: List[str], diff_stats: str) -> str:
    """Simplified retry prompt in English"""
    files_str = ', '.join(staged_files)
    
    return f"""Please analyze this commit briefly:

## 💬 Conversations:
{conversations}

## 📁 Files:
{files_str}

## 📊 Changes:
{diff_stats}

Please respond only in the following JSON format:
{{
  "intent": "Problem or goal to solve",
  "changes": "Changed files and content",
  "context": "Key findings or process"
}}"""


# Export dictionary for compatibility
en_prompts = {
    'main_analysis': main_analysis,
    'simplified_analysis': simplified_analysis
}
