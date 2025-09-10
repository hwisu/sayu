"""Korean prompts for Sayu"""

from typing import List


def main_analysis(conversations: str, staged_files: List[str], diff_stats: str, process_analysis: str) -> str:
    """Main LLM analysis prompt in Korean"""
    files_str = ', '.join(staged_files)
    
    return f"""이 커밋의 효과적인 맥락을 제공하기 위해 분석하세요.

## 🗂 변경된 파일:
{files_str}

## 📊 변경 통계:
{diff_stats}

## 💬 관련 대화:
{conversations}

## 📈 대화 패턴 분석:
{process_analysis}

**핵심 원칙:**
- 나중에 이 커밋을 이해하는 데 도움이 될 맥락 포착에 집중
- 전체 개발 과정을 보여주기 위해 성공과 실패한 시도 모두 포함
- "무엇을" 했는지뿐만 아니라 "왜" 했는지를 문서화

다음 세 가지 핵심 측면으로 JSON을 반환하세요:

{{
  "what_changed": "이 커밋에서 수정된 내용을 명확한 한글 문장으로 설명하세요. 구체적인 파일명과 변경 사항을 자연스러운 문장으로 작성하세요.",
  
  "conversation_flow": "대화의 흐름을 시간순으로 한글 문장으로 설명하세요. '~를 논의했다', '~를 시도했다', '~문제를 발견했다' 등의 형태로 작성하세요.",
  
  "intent": "이 변경의 목적을 간결한 한글 문장으로 설명하세요. 왜 이 작업을 했는지 명확하게 표현하세요."
}}

JSON response:"""


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