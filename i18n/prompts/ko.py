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

다음 JSON 형식으로만 응답해주세요 (간결하고 핵심적인 언어 사용):
{{
  "intent": "이번 커밋으로 해결하려던 구체적인 문제나 목표 (변경된 파일과 대화 내용 기반)",
  "changes": "실제 변경된 파일들의 구체적인 수정 내용과 구현 방법 (파일명과 변경사항 포함)",
  "context": "개발 과정의 주요 발견사항, 문제 해결 과정, 특이점 (간결하게)"
}}"""


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

다음 JSON 형식으로만 응답해주세요:
{{
  "intent": "해결하려던 문제나 목표",
  "changes": "변경된 파일과 내용",
  "context": "주요 발견사항이나 과정"
}}"""


# Export dictionary for compatibility
ko_prompts = {
    'main_analysis': main_analysis,
    'simplified_analysis': simplified_analysis
}
