"""Korean prompts for Sayu"""

from typing import List


def main_analysis(conversations: str, staged_files: List[str], diff_stats: str, process_analysis: str) -> str:
    """Main LLM analysis prompt in Korean"""
    files_str = ', '.join(staged_files)
    
    return f"""이번 커밋의 전체 개발 과정을 분석해주세요.

## 🗂 변경된 파일:
{files_str}

## 📊 변경 통계:
{diff_stats}

## 💬 관련 대화:
{conversations}

## 📈 대화 패턴 분석:
{process_analysis}

**IMPORTANT: 반드시 유효한 JSON만 반환하세요. 마크다운 없이, 코드 블록 없이, 설명 없이 오직 JSON만 출력하세요.**

**전체 개발 흐름 파악을 위한 핵심 지침:**
1. 최종 결과뿐 아니라 과정 전체를 담아주세요
2. 시도했던 모든 접근 방법을 포함 (실패한 것도 포함)
3. 주요 결정 지점과 그 이유를 기록
4. 중요한 에러 메시지나 디버깅 과정의 통찰을 보존
5. 참고한 외부 문서나 리소스가 있다면 언급
6. 성능이나 트레이드오프에 대한 고려사항 포함

Response format (valid JSON only):
{{
  "intent": "초기 문제/목표와 개발 중 이해가 어떻게 발전했는지. 접근 방식의 전환이나 개선 포함",
  "changes": "완전한 변경 목록: 변경된 파일, 영향받은 메서드/함수, 설정 변경, 테스트 추가, 리팩토링 내용. 무엇이 어디서 변경되었는지 구체적으로", 
  "context": "전체 개발 흐름: 초기 접근 → 직면한 문제 → 시도한 해결책 → 디버깅 과정 → 핵심 발견사항 → 의사결정과 근거 → 남은 고려사항. 이 코드가 만들어진 전체 스토리"
}}

JSON response:"""


def simplified_analysis(conversations: str, staged_files: List[str], diff_stats: str) -> str:
    """Simplified retry prompt in Korean"""
    files_str = ', '.join(staged_files)
    
    return f"""이번 커밋의 개발 흐름을 간결하게 분석해주세요:

## 💬 대화:
{conversations}

## 📁 파일:
{files_str}

## 📊 변경사항:
{diff_stats}

**IMPORTANT: 오직 유효한 JSON만 반환하세요. 마크다운이나 설명 없이 JSON만 출력하세요.**

**핵심: 간결하지만 개발 흐름이 완전히 드러나도록**

Response format (valid JSON only):
{{
  "intent": "초기 문제 → 최종 목표 (발전 과정 표현)",
  "changes": "파일별 구체적 위치와 변경 내용", 
  "context": "개발 흐름: 시작 → 도전과제 → 해결책 → 결과"
}}

JSON response:"""


# Export dictionary for compatibility
ko_prompts = {
    'main_analysis': main_analysis,
    'simplified_analysis': simplified_analysis
}
