"""Korean prompts for Sayu"""

from typing import List


def main_analysis(conversations: str, staged_files: List[str], diff_stats: str, process_analysis: str) -> str:
    """Main LLM analysis prompt in Korean - optimized for speed"""
    files_str = ', '.join(staged_files[:10])  # Show more files
    if len(staged_files) > 10:
        files_str += f" 외 {len(staged_files)-10}개"
    
    return f"""이 커밋의 맥락을 분석하여 향후 개발에 도움이 되는 정보를 제공하세요.

## 📁 변경된 파일:
{files_str}

## 📊 변경 통계:
{diff_stats}

## 💬 관련 대화:
{conversations[:3000]}

## 📈 개발 과정 분석:
{process_analysis}

**핵심 원칙:**
- 향후 이 커밋을 이해하는데 도움이 되는 맥락 포착
- 성공한 시도와 실패한 시도 모두 포함하여 전체 개발 과정 표현
- "무엇"이 아닌 "왜"에 초점

다음 세 가지 핵심 요소를 포함한 JSON 반환:

{{
  "what_changed": "이 커밋에서 변경된 모든 내용의 포괄적인 목록. 특정 파일, 함수, 로직 수정 사항과 위치를 상세하고 정확하게 기술",
  
  "conversation_flow": "대화가 어떻게 진행되었는지 개발 여정. 토론이 어떻게 발전했나? 어떤 접근법을 시도했나? 어떤 문제가 발생했고 어떻게 해결했나? 주요 결정 포인트 포함",
  
  "intent": "이러한 변경의 목적. 대화에서 명시적으로 언급되었다면 인용. 그렇지 않으면 맥락에서 추론. 왜 이 작업이 필요했나? 어떤 문제를 해결하나?"
}}

JSON 응답:"""


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
