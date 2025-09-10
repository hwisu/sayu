"""English prompts for Sayu"""

from typing import List


def main_analysis(conversations: str, staged_files: List[str], diff_stats: str, process_analysis: str) -> str:
    """Main LLM analysis prompt in English"""
    files_str = ', '.join(staged_files[:10])  # Limit for better readability
    if len(staged_files) > 10:
        files_str += f" (+{len(staged_files)-10} more)"
    
    return f"""Analyze this commit's context to provide information that helps future developers (including yourself) understand these changes.

## 📁 Changed Files
{files_str}

## 📊 Change Statistics
{diff_stats}

## 💬 Related Conversations (last 3000 chars)
{conversations[:3000]}

## 📈 Development Process Analysis
{process_analysis}

## Instructions

Respond in the following JSON format. Each field must be a **string**:

```json
{{
  "what_changed": "List specific changes comprehensively. Include file names, function/class names, added/modified/removed logic with exact locations. Include technical details and implementation choices.",
  
  "conversation_flow": "Describe the complete development flow chronologically: (1) Initial request/problem → (2) First attempt and results → (3) Challenges faced and solutions → (4) Alternative approaches considered → (5) Final implementation decision. Include reasoning behind technical choices.",
  
  "intent": "Explain the core purpose and motivation for these changes. Quote relevant parts from conversations if explicitly stated, otherwise infer from context. Clearly describe the specific problem being solved and the goal being achieved."
}}
```

## Core Principles
- ✅ Write so future readers understand "why this was implemented this way"
- ✅ Include failed attempts and their reasons to document the full development process
- ✅ Document technical decisions and trade-offs clearly
- ✅ Use specific, searchable technical terms

Return only JSON:"""


def simplified_analysis(conversations: str, staged_files: List[str], diff_stats: str) -> str:
    """Simplified retry prompt in English"""
    files_str = ', '.join(staged_files)
    
    return f"""Provide a concise and clear summary of this commit.

## 💬 Conversation Content
{conversations}

## 📁 Changed Files
{files_str}

## 📊 Change Statistics
{diff_stats}

## Instructions

Return JSON in the following format. Each field should be a concise 1-2 sentence string:

```json
{{
  "what_changed": "Summarize which files and features were changed",
  "conversation_flow": "Describe key steps in the development process",
  "intent": "State the purpose of this change and problem being solved"
}}
```

Return only JSON:"""


# Export dictionary for compatibility
en_prompts = {
    'main_analysis': main_analysis,
    'simplified_analysis': simplified_analysis
}
