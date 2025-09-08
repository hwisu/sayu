import { Event, LLMSummaryResponse } from '../events/types';
import { LLMApiClient } from '../../infra/api/llm';
import { i18n } from '../../i18n';
import { TEXT_CONSTANTS } from '../../shared/constants';

export class LLMSummaryGenerator {
  static async generate(llmEvents: Event[], stagedFiles: string[], diffStats: string): Promise<string> {
    const prompt = this.buildPrompt(llmEvents, stagedFiles, diffStats);
    const response = await LLMApiClient.callLLM(prompt);
    
    try {
      const parsed = JSON.parse(response);
      return this.formatCommitTrailer(parsed);
    } catch (parseError) {
      console.log('[Sayu] JSON parse failed, using raw response');
      return this.formatRawResponse(response);
    }
  }

  static async generateSimplified(llmEvents: Event[], stagedFiles: string[], diffStats: string): Promise<string> {
    const recentConversations = llmEvents
      .slice(-TEXT_CONSTANTS.MAX_SIMPLIFIED_CONVERSATIONS)
      .map(e => `[${e.actor}]: ${e.text.substring(0, TEXT_CONSTANTS.MAX_SIMPLIFIED_LENGTH)}`)
      .join('\n');
      
    const simplePrompt = i18n().getSimplifiedAnalysisPrompt(recentConversations, stagedFiles, diffStats);
    const response = await LLMApiClient.callLLM(simplePrompt);
    
    try {
      const parsed = JSON.parse(response);
      return this.formatCommitTrailer(parsed);
    } catch (parseError) {
      console.log('[Sayu] JSON parse failed, using raw response');
      return this.formatRawResponse(response);
    }
  }

  private static buildPrompt(llmEvents: Event[], stagedFiles: string[], diffStats: string): string {
    const conversations = llmEvents
      .slice(-TEXT_CONSTANTS.MAX_CONVERSATION_COUNT)
      .map(e => `[${e.actor}]: ${e.text.substring(0, TEXT_CONSTANTS.MAX_CONVERSATION_LENGTH)}`)
      .join('\n');
    
    const processAnalysis = this.analyzeConversationProcess(llmEvents);
    
    return i18n().getMainAnalysisPrompt(conversations, stagedFiles, diffStats, processAnalysis);
  }

  private static formatCommitTrailer(parsed: LLMSummaryResponse): string {
    const lines: string[] = [];
    const outputs = i18n().getOutputs();
    
    lines.push('---');
    lines.push(outputs.trailerHeader);
    lines.push('');
    
    if (parsed.intent) {
      lines.push(outputs.trailerLabels.intent);
      lines.push(this.wrapText(parsed.intent, 2));
      lines.push('');
    }
    
    if (parsed.changes) {
      lines.push(outputs.trailerLabels.changes);
      lines.push(this.wrapText(parsed.changes, 2));
      lines.push('');
    }
    
    if (parsed.context) {
      lines.push(outputs.trailerLabels.context);
      lines.push(this.wrapText(parsed.context, 2));
      lines.push('');
    }
    
    lines.push('---');
    
    return lines.join('\n');
  }

  private static wrapText(text: string, indent: number = 0): string {
    const maxLineLength = TEXT_CONSTANTS.MAX_LINE_LENGTH;
    const indentStr = ' '.repeat(indent);
    const words = text.split(' ');
    const lines: string[] = [];
    let currentLine = indentStr;
    
    for (const word of words) {
      if (currentLine.length + word.length + 1 <= maxLineLength) {
        if (currentLine === indentStr) {
          currentLine += word;
        } else {
          currentLine += ' ' + word;
        }
      } else {
        lines.push(currentLine);
        currentLine = indentStr + word;
      }
    }
    
    if (currentLine.trim()) {
      lines.push(currentLine);
    }
    
    return lines.join('\n');
  }

  private static formatRawResponse(text: string): string {
    const lines: string[] = [];
    lines.push('---');
    lines.push('AI-Context (sayu)');
    
    const cleanText = text.replace(/[\n\r]+/g, ' ').trim();
    if (cleanText.length > TEXT_CONSTANTS.MAX_RAW_RESPONSE_LENGTH) {
      lines.push(`Summary: ${cleanText.substring(0, TEXT_CONSTANTS.MAX_RAW_RESPONSE_LENGTH)}...`);
    } else {
      lines.push(`Summary: ${cleanText}`);
    }
    
    lines.push('---');
    
    return lines.join('\n');
  }

  private static analyzeConversationProcess(llmEvents: Event[]): string {
    if (llmEvents.length === 0) {
      return "대화 없음: 코드 변경만 수행됨";
    }
    
    const analysis: string[] = [];
    
    const userEvents = llmEvents.filter(e => e.actor === 'user');
    const assistantEvents = llmEvents.filter(e => e.actor === 'assistant');
    
    analysis.push(`대화 총 ${llmEvents.length}회 (사용자: ${userEvents.length}, 어시스턴트: ${assistantEvents.length})`);
    
    const questions = userEvents.filter(e => e.text.includes('?') || e.text.includes('어떻게') || e.text.includes('왜'));
    if (questions.length > 0) {
      analysis.push(`${questions.length}개의 질문/문의사항 포함`);
    }
    
    const problemKeywords = ['문제', '오류', '에러', '안됨', '실패', '버그'];
    const problemEvents = llmEvents.filter(e => 
      problemKeywords.some(keyword => e.text.includes(keyword))
    );
    if (problemEvents.length > 0) {
      analysis.push(`문제 해결 과정: ${problemEvents.length}회 언급`);
    }
    
    const retryKeywords = ['다시', '재시도', '또', '한번 더'];
    const retryEvents = llmEvents.filter(e => 
      retryKeywords.some(keyword => e.text.includes(keyword))
    );
    if (retryEvents.length > 0) {
      analysis.push(`반복/재시도 과정: ${retryEvents.length}회 발생`);
    }
    
    const toolEvents = llmEvents.filter(e => e.text.includes('[Tool:'));
    if (toolEvents.length > 0) {
      analysis.push(`도구 사용: ${toolEvents.length}회`);
    }
    
    const unusualPatterns = [];
    
    if (llmEvents.length > 50) {
      unusualPatterns.push(`장시간 세션 (${llmEvents.length}회 대화)`);
    }
    
    const shortResponses = userEvents.filter(e => e.text.length < 10);
    if (shortResponses.length > 3) {
      unusualPatterns.push(`짧은 응답 연속 (${shortResponses.length}회)`);
    }
    
    const allText = llmEvents.map(e => e.text).join(' ');
    const keywordCounts = new Map();
    ['최적화', '성능', '버그', '테스트', '리팩토링'].forEach(keyword => {
      const count = (allText.match(new RegExp(keyword, 'g')) || []).length;
      if (count > 3) keywordCounts.set(keyword, count);
    });
    
    if (keywordCounts.size > 0) {
      const keywords = Array.from(keywordCounts.entries())
        .map(([word, count]) => `${word}(${count}회)`)
        .join(', ');
      unusualPatterns.push(`반복 키워드: ${keywords}`);
    }
    
    if (unusualPatterns.length > 0) {
      analysis.push(`특이점: ${unusualPatterns.join(', ')}`);
    }
    
    return analysis.join(' / ');
  }
}