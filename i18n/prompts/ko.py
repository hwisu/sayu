"""Korean prompts for Sayu"""

from typing import List


def main_analysis(conversations: str, staged_files: List[str], diff_stats: str, process_analysis: str) -> str:
    """Main LLM analysis prompt in Korean - optimized for speed"""
    files_str = ', '.join(staged_files[:5])  # Limit to 5 files for speed
    if len(staged_files) > 5:
        files_str += f" (+{len(staged_files)-5} more)"
    
    return f"""커밋 맥락 분석:

파일: {files_str}
통계: {diff_stats}

대화:
{conversations[:2000]}  # Limit conversation length

JSON 반환:
{{
  "what_changed": "수정 내용 한글 설명",
  "conversation_flow": "대화 흐름 요약", 
  "intent": "변경 목적"
}}"""


def simplified_analysis(conversations: str, staged_files: List[str], diff_stats: str) -> str:
    """Simplified retry prompt in Korean"""
    files_str = ', '.join(staged_files)
    
    return f"""맥락을 위한 간결한 커밋 분석을 제공하세요.

## 💬 대화:
{conversations}

## 📁 파일:
{files_str}

## 📊 변경사항:
{diff_stats}

간단한 JSON 요약 반환:

{{
  "what_changed": "주요 수정 사항을 한글 문장으로 설명",
  "conversation_flow": "개발 과정을 한글 문장으로 설명",
  "intent": "변경 목적을 한글 문장으로 설명"
}}

JSON response:"""


# Export dictionary for compatibility
ko_prompts = {
    'main_analysis': main_analysis,
    'simplified_analysis': simplified_analysis
}
