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
  "what_changed": "이 커밋에서 만들어진 모든 변경 사항의 포괄적인 목록. 구체적인 파일, 함수, 로직 수정 사항과 위치를 포함하세요. 상세하고 정확하게.",
  
  "conversation_flow": "대화에서 나타난 개발 여정. 논의가 어떻게 진행되었나? 어떤 접근법을 시도했나? 어떤 도전이 있었고 어떻게 해결했나? 주요 결정 지점 포함.",
  
  "intent": "이러한 변경의 목적. 대화에서 명시적으로 언급되었다면 인용하고, 그렇지 않다면 맥락에서 추론. 왜 이 작업이 필요했나? 어떤 문제를 해결하나?"
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
  "what_changed": "주요 수정 사항 (파일, 함수, 로직)",
  "conversation_flow": "개발 논의가 어떻게 진행되었는지",
  "intent": "변경의 목적 (명시적이거나 추론된)"
}}

JSON response:"""


# Export dictionary for compatibility
ko_prompts = {
    'main_analysis': main_analysis,
    'simplified_analysis': simplified_analysis
}
