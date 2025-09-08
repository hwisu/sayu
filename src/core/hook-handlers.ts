import fs from 'fs';
import path from 'path';
import { ShellExecutor } from './shell';
import { ConfigManager } from './config';
import { GitHookManager } from './git-hooks';
import { Event, Config, LLMSummaryResponse } from './types';
import { EventCollector } from './collectors/event-collector';
import { GitInfo } from './git/git-info';
import { EventFilter } from './filters/event-filter';
import { ClaudeCollector } from '../collectors/llm-claude';
import { CursorCollector } from '../collectors/llm-cursor';
import { CliCollector } from '../collectors/cli';
import { EventStore } from './database';
import { i18n } from './i18n';
import { LLMApiClient } from './llm-api';
import { TIME_CONSTANTS, TEXT_CONSTANTS, FILTER_CONSTANTS } from './constants';
import { ErrorHandler } from './error-handler';
import * as dotenv from 'dotenv';

export class HookHandlers {

  // commit-msg 훅 핸들러 - 경량화 버전
  static async handleCommitMsg(commitMsgFile: string): Promise<void> {
    try {
      const repoRoot = GitHookManager.getRepoRoot();
      if (!repoRoot) return;
      
      // .env 파일 로드 (repo root에서)
      const envPath = path.join(repoRoot, '.env');
      if (fs.existsSync(envPath)) {
        dotenv.config({ path: envPath });
      }

      const configManager = new ConfigManager(repoRoot);
      const userConfig = configManager.getEffectiveConfig();
      if (!userConfig.commitTrailer) return;

      // 빈 커밋 검증
      const checkStagedFiles = GitInfo.getStagedFiles();
      const checkHasChanges = GitInfo.hasActualChanges();
      
      if (checkStagedFiles.length === 0 && !checkHasChanges) {
        console.error(i18n().t('errors.emptyCommit'));
        console.error(i18n().t('errors.useAllowEmpty'));
        process.exit(1);
      }
      
      if (checkStagedFiles.length === 0 && checkHasChanges) {
        console.log(i18n().t('errors.noStagedButChanges'));
      }

      // 실시간으로 LLM 대화만 가져오기
      const llmEvents: Event[] = [];
      const now = Date.now();
      
      // 마지막 커밋 시간 찾기
      const store = new EventStore();
      const lastCommitTime = store.getLastCommitTime(repoRoot);
      
      // 마지막 커밋 시간부터 수집 (첫 커밋인 경우만 설정 시간 적용)
      const configLookback = TIME_CONSTANTS.DEFAULT_LOOKBACK_HOURS * 60 * 60 * 1000;
      
      const sinceMs = lastCommitTime || now - configLookback;
      store.close();
      
      // Claude 대화 가져오기 (로그에서 직접) - 항상 시도 (opinionated)
      const fullConfig = configManager.get();
      try {
        const claudeCollector = new ClaudeCollector(repoRoot);
        const claudeEvents = await claudeCollector.pullSince(sinceMs, now, fullConfig);
        
        // 효용이 높은 이벤트만 선별 (스마트 필터링)
        const filteredClaudeEvents = this.filterHighValueEvents(claudeEvents);
        
        if (claudeEvents.length !== filteredClaudeEvents.length) {
          console.log(`[Sayu] Claude events filtered: ${claudeEvents.length} → ${filteredClaudeEvents.length} (smart filter)`);
        }
        
        llmEvents.push(...filteredClaudeEvents);
      } catch (error) {
        // Claude 없으면 조용히 무시
      }
      
      // Cursor 대화 가져오기 (DB에서 직접) - 항상 시도 (opinionated)
      try {
        const cursorCollector = new CursorCollector(repoRoot);
        const cursorEvents = await cursorCollector.pullSince(sinceMs, now, fullConfig);
        llmEvents.push(...cursorEvents);
      } catch (error) {
        // Cursor 없으면 조용히 무시
      }
      
      // CLI 커맨드 가져오기 (JSONL 로그에서) - 항상 시도 (opinionated)
      try {
        const cliCollector = new CliCollector(repoRoot);
        const cliEvents = await cliCollector.pullSince(sinceMs, now, fullConfig);
        llmEvents.push(...cliEvents);
      } catch (error) {
        // CLI 없으면 조용히 무시
      }
      
      // 현재 변경사항 정보
      const stagedFiles = GitInfo.getStagedFiles();
      const diffStats = GitInfo.getDiffStats();
      
      // LLM을 사용한 의미있는 요약 생성 시도
      let summary: string;
      
      console.log(`[Sayu] ${i18n().t('cli.apiKeysAvailable')}:`, LLMApiClient.getAvailableAPIs());
      
      console.log(`[Sayu] Collected ${llmEvents.length} ${i18n().t('cli.collectedEvents')}`);
      
      const availableAPIs = LLMApiClient.getAvailableAPIs();
      if (availableAPIs.gemini || availableAPIs.openai || availableAPIs.anthropic) {
        console.log(`[Sayu] ${i18n().t('cli.attemptingGeneration')}`);
        try {
          summary = await this.generateLLMSummary(llmEvents, stagedFiles, diffStats);
          console.log(`[Sayu] ${i18n().t('cli.generationSuccess')}`);
          console.log(`[Sayu] ${i18n().t('cli.summaryLength')} ${summary.length} characters`);
        } catch (error) {
          console.error('[Sayu] LLM API failed, trying again with simplified prompt:', error instanceof Error ? error.message : String(error));
          
          // 대신 간단한 프롬프트로 재시도
          try {
            summary = await this.generateSimplifiedLLMSummary(llmEvents, stagedFiles, diffStats);
            console.log('[Sayu] Simplified LLM summary generated successfully');
          } catch (retryError) {
            console.error('[Sayu] All LLM attempts failed, using minimal summary');
            summary = this.generateMinimalSummary(llmEvents, stagedFiles, diffStats);
          }
        }
      } else {
        console.log('[Sayu] No API keys found, using minimal summary');
        summary = this.generateMinimalSummary(llmEvents, stagedFiles, diffStats);
      }
      
      // 커밋 메시지에 트레일러 추가
      if (summary) {
        const currentMsg = fs.readFileSync(commitMsgFile, 'utf-8');
        
        // 이미 Sayu 트레일러가 있으면 스킵
        if (currentMsg.includes('AI-Context (sayu)')) {
          return;
        }
        
        const newMsg = currentMsg.trimEnd() + '\n\n' + summary;
        fs.writeFileSync(commitMsgFile, newMsg);
      }
      
      // 최소한의 이벤트만 DB에 저장 (커밋 기록용)
      const commitEvent: Event = {
        id: `commit-${Date.now()}`,
        ts: now,
        source: 'git',
        kind: 'commit',
        repo: repoRoot,
        cwd: repoRoot,
        file: null,
        range: null,
        actor: 'user',
        text: fs.readFileSync(commitMsgFile, 'utf-8').split('\n')[0], // 첫 줄만
        url: null,
        meta: {
          filesCount: `${stagedFiles.length}`,
          llmContext: llmEvents.length > 0 ? 'true' : 'false'
        }
      };
      
      const store2 = new EventStore();
      store2.insert(commitEvent);
      store2.close();
      
    } catch (error) {
      // Fail-open: 에러 발생해도 커밋은 계속
      ErrorHandler.handle(error, {
        operation: 'commit-msg-hook',
        recoverable: true,
        details: 'Sayu 훅 실행 중 오류가 발생했지만 커밋은 계속됩니다'
      });
    }
  }

  // post-commit 훅 핸들러 (현재 미사용)
  static async handlePostCommit(): Promise<void> {
    try {
      console.log('Post-commit: Hook executed');
    } catch (error) {
      console.error('Sayu post-commit hook error:', error);
    }
  }
  
  // 간단한 프롬프트로 LLM 재시도
  private static async generateSimplifiedLLMSummary(llmEvents: Event[], stagedFiles: string[], diffStats: string): Promise<string> {
    // 간단한 분석을 위한 개선된 프롬프트
    const recentConversations = llmEvents
      .slice(-TEXT_CONSTANTS.MAX_SIMPLIFIED_CONVERSATIONS)
      .map(e => `[${e.actor}]: ${e.text.substring(0, TEXT_CONSTANTS.MAX_SIMPLIFIED_LENGTH)}`)
      .join('\n');
      
    const simplePrompt = i18n().getSimplifiedAnalysisPrompt(recentConversations, stagedFiles, diffStats);
    const response = await LLMApiClient.callLLM(simplePrompt);
    
    // JSON 응답을 파싱하여 구조화된 커밋 트레일러 생성
    try {
      const parsed = JSON.parse(response);
      return this.formatCommitTrailer(parsed);
    } catch (parseError) {
      console.log('[Sayu] JSON parse failed, using raw response');
      return this.formatRawResponse(response);
    }
  }

  // 최소한의 요약 (마지막 resort)
  private static generateMinimalSummary(llmEvents: Event[], stagedFiles: string[], diffStats: string): string {
    const lines: string[] = [];
    lines.push('---');
    lines.push('AI-Context (sayu)');
    
    // 변경된 파일
    if (stagedFiles.length > 0) {
      const fileList = stagedFiles.slice(0, TEXT_CONSTANTS.MAX_FILE_DISPLAY).join(', ');
      const more = stagedFiles.length > TEXT_CONSTANTS.MAX_FILE_DISPLAY ? ` (+${stagedFiles.length - TEXT_CONSTANTS.MAX_FILE_DISPLAY} more)` : '';
      lines.push(`Files: ${fileList}${more}`);
    }
    
    // LLM 이벤트 정보
    if (llmEvents.length > 0) {
      const tools = new Set(llmEvents.map(e => e.meta?.tool).filter(Boolean));
      const toolList = Array.from(tools).join(', ') || 'unknown';
      lines.push(`Events: ${llmEvents.length} LLM interactions (${toolList})`);
    } else {
      lines.push(`Events: Code changes only`);
    }
    
    lines.push('---');
    
    return lines.join('\n');
  }
  
  // LLM을 사용한 의미있는 요약 생성
  private static async generateLLMSummary(llmEvents: Event[], stagedFiles: string[], diffStats: string): Promise<string> {
    const prompt = this.buildLLMPrompt(llmEvents, stagedFiles, diffStats);
    const response = await LLMApiClient.callLLM(prompt);
    
    // JSON 응답을 파싱하여 구조화된 커밋 트레일러 생성
    try {
      const parsed = JSON.parse(response);
      return this.formatCommitTrailer(parsed);
    } catch (parseError) {
      console.log('[Sayu] JSON parse failed, using raw response');
      return this.formatRawResponse(response);
    }
  }
  
  // LLM 프롬프트 생성
  private static buildLLMPrompt(llmEvents: Event[], stagedFiles: string[], diffStats: string): string {
    const conversations = llmEvents
      .slice(-TEXT_CONSTANTS.MAX_CONVERSATION_COUNT)
      .map(e => `[${e.actor}]: ${e.text.substring(0, TEXT_CONSTANTS.MAX_CONVERSATION_LENGTH)}`)
      .join('\n');
    
    // 대화 흐름 분석
    const processAnalysis = this.analyzeConversationProcess(llmEvents);
    
    return i18n().getMainAnalysisPrompt(conversations, stagedFiles, diffStats, processAnalysis);
  }
  
  
  // JSON 응답을 구조화된 커밋 트레일러로 변환
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

  // 텍스트를 적절한 길이로 줄바꿈하고 들여쓰기 적용
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
  
  // 원시 응답을 기본 형식으로 변환
  private static formatRawResponse(text: string): string {
    const lines: string[] = [];
    lines.push('---');
    lines.push('AI-Context (sayu)');
    
    // 응답에서 중요한 정보 추출 시도
    const cleanText = text.replace(/[\n\r]+/g, ' ').trim();
    if (cleanText.length > TEXT_CONSTANTS.MAX_RAW_RESPONSE_LENGTH) {
      lines.push(`Summary: ${cleanText.substring(0, TEXT_CONSTANTS.MAX_RAW_RESPONSE_LENGTH)}...`);
    } else {
      lines.push(`Summary: ${cleanText}`);
    }
    
    lines.push('---');
    
    return lines.join('\n');
  }
  
  // 효용이 높은 이벤트만 선별하는 스마트 필터
  private static filterHighValueEvents(events: Event[]): Event[] {
    const highValueEvents: Event[] = [];
    const maxEvents = TEXT_CONSTANTS.MAX_HIGH_VALUE_EVENTS;
    
    for (const event of events.reverse()) { // 최신부터 처리
      if (highValueEvents.length >= maxEvents) break;
      
      const text = event.text;
      const isHighValue = this.isHighValueEvent(event, text);
      
      if (isHighValue) {
        highValueEvents.unshift(event); // 원래 순서 유지
      }
    }
    
    return highValueEvents;
  }
  
  // 이벤트의 효용성 판단
  private static isHighValueEvent(event: Event, text: string): boolean {
    // 사용자 이벤트는 모두 중요 (길이 무관)
    if (event.actor === 'user') {
      // 도구 결과는 제외 (시스템 메시지)
      if (text.startsWith('[Result:') || text.startsWith('[Tool result:')) {
        return false;
      }
      // 빈 메시지는 제외
      if (text.trim().length === 0) {
        return false;
      }
      // 모든 사용자 메시지는 중요 (짧은 응답도 포함)
      return true;
    }
    
    // 어시스턴트 이벤트 필터링
    if (event.actor === 'assistant') {
      // 도구 사용은 제외
      if (text.startsWith('[Tool:') || text.includes('[Tool:')) {
        return false;
      }
      
      // 매우 짧은 응답은 제외
      if (text.length < TEXT_CONSTANTS.MIN_RESPONSE_LENGTH) {
        return false;
      }
      
      // 단순 확인/완료 메시지는 제외
      const lowValuePatterns = [
        /^완료|^성공|^확인|^좋습니다|^네,?\s*$|^알겠습니다/,
        /빌드.*완료|테스트.*완료|설치.*완료/,
        /시간.*초과|제한.*도달/
      ];
      
      for (const pattern of lowValuePatterns) {
        if (pattern.test(text)) {
          return false;
        }
      }
      
      return true;
    }
    
    return false;
  }
  
  // 대화 과정 분석
  private static analyzeConversationProcess(llmEvents: Event[]): string {
    if (llmEvents.length === 0) {
      return "대화 없음: 코드 변경만 수행됨";
    }
    
    const analysis: string[] = [];
    
    // 대화 패턴 분석
    const userEvents = llmEvents.filter(e => e.actor === 'user');
    const assistantEvents = llmEvents.filter(e => e.actor === 'assistant');
    
    analysis.push(`대화 총 ${llmEvents.length}회 (사용자: ${userEvents.length}, 어시스턴트: ${assistantEvents.length})`);
    
    // 질문 패턴 분석
    const questions = userEvents.filter(e => e.text.includes('?') || e.text.includes('어떻게') || e.text.includes('왜'));
    if (questions.length > 0) {
      analysis.push(`${questions.length}개의 질문/문의사항 포함`);
    }
    
    // 문제 해결 과정 감지
    const problemKeywords = ['문제', '오류', '에러', '안됨', '실패', '버그'];
    const problemEvents = llmEvents.filter(e => 
      problemKeywords.some(keyword => e.text.includes(keyword))
    );
    if (problemEvents.length > 0) {
      analysis.push(`문제 해결 과정: ${problemEvents.length}회 언급`);
    }
    
    // 반복/재시도 패턴 감지
    const retryKeywords = ['다시', '재시도', '또', '한번 더'];
    const retryEvents = llmEvents.filter(e => 
      retryKeywords.some(keyword => e.text.includes(keyword))
    );
    if (retryEvents.length > 0) {
      analysis.push(`반복/재시도 과정: ${retryEvents.length}회 발생`);
    }
    
    // 도구 사용 빈도
    const toolEvents = llmEvents.filter(e => e.text.includes('[Tool:'));
    if (toolEvents.length > 0) {
      analysis.push(`도구 사용: ${toolEvents.length}회`);
    }
    
    // 특이점 감지
    const unusualPatterns = [];
    
    // 매우 긴 대화 세션
    if (llmEvents.length > 50) {
      unusualPatterns.push(`장시간 세션 (${llmEvents.length}회 대화)`);
    }
    
    // 연속된 짧은 응답들
    const shortResponses = userEvents.filter(e => e.text.length < 10);
    if (shortResponses.length > 3) {
      unusualPatterns.push(`짧은 응답 연속 (${shortResponses.length}회)`);
    }
    
    // 특정 키워드 반복
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
