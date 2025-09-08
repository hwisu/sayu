import { koPrompts } from './prompts/ko';
import { enPrompts } from './prompts/en';
import { koOutputs } from './outputs/ko';
import { enOutputs } from './outputs/en';

export type SupportedLanguage = 'ko' | 'en';

export class I18nManager {
  private static instance: I18nManager;
  private currentLanguage: SupportedLanguage;

  private constructor() {
    // 환경변수 SAYU_LANG에서 언어 설정을 가져오거나 기본값 'ko' 사용
    const envLang = process.env.SAYU_LANG?.toLowerCase();
    this.currentLanguage = (envLang === 'en' || envLang === 'ko') ? envLang : 'ko';
  }

  public static getInstance(): I18nManager {
    if (!I18nManager.instance) {
      I18nManager.instance = new I18nManager();
    }
    return I18nManager.instance;
  }

  public getLanguage(): SupportedLanguage {
    return this.currentLanguage;
  }

  public setLanguage(lang: SupportedLanguage): void {
    this.currentLanguage = lang;
  }

  // 프롬프트 템플릿 가져오기
  public getPrompts() {
    return this.currentLanguage === 'ko' ? koPrompts : enPrompts;
  }

  // 출력 템플릿 가져오기
  public getOutputs() {
    return this.currentLanguage === 'ko' ? koOutputs : enOutputs;
  }

  // 간편한 번역 함수들
  public t(path: string, ...args: any[]): string {
    const outputs = this.getOutputs();
    const keys = path.split('.');
    let current: any = outputs;
    
    for (const key of keys) {
      current = current[key];
      if (current === undefined) {
        console.warn(`Translation key not found: ${path}`);
        return path; // 키를 찾을 수 없으면 경로 자체를 반환
      }
    }
    
    // 함수인 경우 인자를 전달하여 실행
    if (typeof current === 'function') {
      return current(...args);
    }
    
    return current;
  }

  // 프롬프트 생성 함수들
  public getMainAnalysisPrompt(conversations: string, stagedFiles: string[], diffStats: string, processAnalysis: string): string {
    const prompts = this.getPrompts();
    return prompts.mainAnalysis(conversations, stagedFiles, diffStats, processAnalysis);
  }

  public getSimplifiedAnalysisPrompt(conversations: string, stagedFiles: string[], diffStats: string): string {
    const prompts = this.getPrompts();
    return prompts.simplifiedAnalysis(conversations, stagedFiles, diffStats);
  }
}

// 전역 인스턴스 접근 함수
export const i18n = () => I18nManager.getInstance();
