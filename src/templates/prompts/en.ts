export const enPrompts = {
  // Main LLM analysis prompt
  mainAnalysis: (conversations: string, stagedFiles: string[], diffStats: string, processAnalysis: string) => `
Analyze this commit to generate concise context.

## 🗂 Changed Files:
${stagedFiles.join(', ')}

## 📊 Change Statistics:
${diffStats}

## 💬 Related Conversations:
${conversations}

## 📈 Conversation Pattern Analysis:
${processAnalysis}

Please respond only in the following JSON format (use concise and essential language):
{
  "intent": "Specific problem or goal this commit aimed to solve (based on changed files and conversation content)",
  "changes": "Concrete modifications in changed files and implementation methods (include file names and changes)",
  "context": "Key findings, problem-solving process, and notable points from development (concisely)"
}`,

  // Simplified retry prompt
  simplifiedAnalysis: (conversations: string, stagedFiles: string[], diffStats: string) => `
Please analyze this commit briefly:

## 💬 Conversations:
${conversations}

## 📁 Files:
${stagedFiles.join(', ')}

## 📊 Changes:
${diffStats}

Please respond only in the following JSON format:
{
  "intent": "Problem or goal to solve",
  "changes": "Changed files and content",
  "context": "Key findings or process"
}`
};
