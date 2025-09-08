export const koPrompts = {
  // 메인 LLM 분석 프롬프트
  mainAnalysis: (conversations: string, stagedFiles: string[], diffStats: string, processAnalysis: string) => `
이번 커밋을 분석하여 간결한 컨텍스트를 생성해주세요.

## 🗂 변경된 파일:
${stagedFiles.join(', ')}

## 📊 변경 통계:
${diffStats}

## 💬 관련 대화:
${conversations}

## 📈 대화 패턴 분석:
${processAnalysis}

다음 JSON 형식으로만 응답해주세요 (간결하고 핵심적인 언어 사용):
{
  "intent": "이번 커밋으로 해결하려던 구체적인 문제나 목표 (변경된 파일과 대화 내용 기반)",
  "changes": "실제 변경된 파일들의 구체적인 수정 내용과 구현 방법 (파일명과 변경사항 포함)",
  "context": "개발 과정의 주요 발견사항, 문제 해결 과정, 특이점 (간결하게)"
}`,

  // 간단한 재시도 프롬프트
  simplifiedAnalysis: (conversations: string, stagedFiles: string[], diffStats: string) => `
이번 커밋을 간단히 분석해주세요:

## 💬 대화:
${conversations}

## 📁 파일:
${stagedFiles.join(', ')}

## 📊 변경사항:
${diffStats}

다음 JSON 형식으로만 응답해주세요:
{
  "intent": "해결하려던 문제나 목표",
  "changes": "변경된 파일과 내용",
  "context": "주요 발견사항이나 과정"
}`
};
