"""Korean prompts for Sayu"""

from typing import List


def main_analysis(conversations: str, staged_files: List[str], diff_stats: str, process_analysis: str) -> str:
    """Main LLM analysis prompt in Korean"""
    files_str = ', '.join(staged_files)
    
    return f"""이번 커밋을 분석하여 간결한 컨텍스트를 생성해주세요.

## 🗂 변경된 파일:
{files_str}

## 📊 변경 통계:
{diff_stats}

## 💬 관련 대화:
{conversations}

## 📈 대화 패턴 분석:
{process_analysis}

**IMPORTANT: 반드시 유효한 JSON만 반환하세요. 마크다운 없이, 코드 블록 없이, 설명 없이 오직 JSON만 출력하세요.**

Response format (valid JSON only):
{{
  "intent": "이번 커밋으로 해결하려던 구체적인 문제나 목표 (변경된 파일과 대화 내용 기반)",
  "changes": "실제 변경된 파일들의 구체적인 수정 내용과 구현 방법 (파일명과 변경사항 포함)",
  "context": "개발 과정의 주요 발견사항, 문제 해결 과정, 특이점 (간결하게)"
}}

JSON response:"""


def simplified_analysis(conversations: str, staged_files: List[str], diff_stats: str) -> str:
    """Simplified retry prompt in Korean"""
    files_str = ', '.join(staged_files)
    
    return f"""이번 커밋을 간단히 분석해주세요:

## 💬 대화:
{conversations}

## 📁 파일:
{files_str}

## 📊 변경사항:
{diff_stats}

**IMPORTANT: 오직 유효한 JSON만 반환하세요. 마크다운이나 설명 없이 JSON만 출력하세요.**

Response format (valid JSON only):
{{
  "intent": "해결하려던 문제나 목표",
  "changes": "변경된 파일과 내용", 
  "context": "주요 발견사항이나 과정"
}}

JSON response:"""


# Export dictionary for compatibility
ko_prompts = {
    'main_analysis': main_analysis,
    'simplified_analysis': simplified_analysis
}
