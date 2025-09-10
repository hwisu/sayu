"""Korean prompts for Sayu"""

from typing import List


def main_analysis(conversations: str, staged_files: List[str], diff_stats: str, process_analysis: str) -> str:
    """Main LLM analysis prompt in Korean - optimized for speed"""
    files_str = ', '.join(staged_files[:10])  # Show more files
    if len(staged_files) > 10:
        files_str += f" 외 {len(staged_files)-10}개"
    
    return f"""이 커밋의 컨텍스트를 분석하여 미래의 개발자(당신 포함)가 이 변경사항을 이해하는데 필요한 정보를 제공하세요.

## 📁 변경된 파일
{files_str}

## 📊 변경 통계
{diff_stats}

## 💬 관련 대화 (최근 3000자)
{conversations[:3000]}

## 📈 개발 과정 분석
{process_analysis}

## 지시사항

다음 JSON 형식으로 응답하세요. 각 필드는 **반드시 문자열(string)**이어야 합니다:

```json
{{
  "what_changed": "변경된 내용을 구체적으로 나열하세요. 파일명, 함수/클래스명, 추가/수정/삭제된 로직을 정확한 위치와 함께 기술하세요. 기술적 세부사항을 포함하여 구현 선택사항을 명시하세요.",
  
  "conversation_flow": "개발 과정의 전체 흐름을 시간 순서대로 설명하세요. (1) 초기 요청/문제 → (2) 첫 번째 시도와 결과 → (3) 직면한 문제와 해결 방법 → (4) 대안 검토 과정 → (5) 최종 구현 결정. 기술적 선택의 이유를 포함하세요.",
  
  "intent": "이 변경사항의 핵심 목적과 동기를 설명하세요. 대화에서 명시된 경우 관련 부분을 인용하고, 그렇지 않은 경우 컨텍스트에서 추론하세요. 해결하려는 구체적 문제와 달성하려는 목표를 명확히 기술하세요."
}}
```

## 핵심 원칙
- ✅ 미래에 이 코드를 보는 사람이 "왜 이렇게 구현했는지" 이해할 수 있도록 작성
- ✅ 실패한 시도와 그 이유도 포함하여 전체 개발 과정을 투명하게 기록
- ✅ 기술적 결정과 트레이드오프를 명확히 문서화
- ✅ 구체적이고 검색 가능한 기술 용어 사용

JSON만 반환하세요:"""


def simplified_analysis(conversations: str, staged_files: List[str], diff_stats: str) -> str:
    """Simplified retry prompt in Korean"""
    files_str = ', '.join(staged_files)
    
    return f"""이 커밋에 대한 간결하고 명확한 요약을 제공하세요.

## 💬 대화 내용
{conversations}

## 📁 변경된 파일
{files_str}

## 📊 변경 통계
{diff_stats}

## 지시사항

다음 형식의 JSON을 반환하세요. 각 필드는 1-2문장의 간결한 문자열이어야 합니다:

```json
{{
  "what_changed": "어떤 파일과 기능이 변경되었는지 핵심만 요약",
  "conversation_flow": "개발이 어떻게 진행되었는지 주요 단계만 설명",
  "intent": "이 변경을 한 목적과 해결하려는 문제"
}}
```

JSON만 반환하세요:"""


# Export dictionary for compatibility
ko_prompts = {
    'main_analysis': main_analysis,
    'simplified_analysis': simplified_analysis
}
