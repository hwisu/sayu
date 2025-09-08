import { exec } from 'child_process';
import { promisify } from 'util';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import { LLM_CONSTANTS } from './constants';

const execAsync = promisify(exec);

/**
 * LLM API 호출을 담당하는 유틸리티 클래스
 * Gemini, OpenAI, Anthropic API를 지원하며 우선순위에 따라 사용 가능한 API를 호출
 */
export class LLMApiClient {
  
  /**
   * 사용 가능한 API 키 확인 및 우선순위에 따른 LLM 호출
   */
  static async callLLM(prompt: string): Promise<string> {
    if (process.env.GEMINI_API_KEY) {
      return await this.callGemini(prompt);
    } else if (process.env.OPENAI_API_KEY) {
      return await this.callOpenAI(prompt);
    } else if (process.env.ANTHROPIC_API_KEY) {
      return await this.callAnthropic(prompt);
    }
    
    throw new Error('No LLM API key found');
  }

  /**
   * 사용 가능한 API 키 목록 반환
   */
  static getAvailableAPIs(): { [key: string]: boolean } {
    return {
      gemini: !!process.env.GEMINI_API_KEY,
      openai: !!process.env.OPENAI_API_KEY,
      anthropic: !!process.env.ANTHROPIC_API_KEY
    };
  }

  /**
   * Gemini API 호출
   */
  private static async callGemini(prompt: string): Promise<string> {
    const apiKey = process.env.GEMINI_API_KEY;
    
    if (!apiKey) {
      throw new Error('GEMINI_API_KEY not found in environment');
    }
    
    const payload = {
      contents: [{
        parts: [{
          text: prompt
        }]
      }],
      generationConfig: {
        temperature: LLM_CONSTANTS.TEMPERATURE,
        maxOutputTokens: LLM_CONSTANTS.MAX_OUTPUT_TOKENS,
        candidateCount: 1,
        responseMimeType: "application/json"
      }
    };
    
    // 임시 파일에 JSON payload 저장 (이스케이핑 문제 해결)
    const tempFile = path.join(os.tmpdir(), `sayu-gemini-${Date.now()}.json`);
    fs.writeFileSync(tempFile, JSON.stringify(payload));
    
    try {
      const curlCommand = `curl -s -X POST \
        -H "Content-Type: application/json" \
        -d @"${tempFile}" \
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${apiKey}"`;
      
      const { stdout } = await execAsync(curlCommand);
      const response = JSON.parse(stdout);
      
      if (response.candidates && response.candidates[0]) {
        const content = response.candidates[0].content;
        if (content && content.parts && content.parts[0]) {
          return content.parts[0].text.trim();
        }
      }
      
      throw new Error('Invalid Gemini response structure');
    } finally {
      // 임시 파일 정리
      if (fs.existsSync(tempFile)) {
        fs.unlinkSync(tempFile);
      }
    }
  }

  /**
   * OpenAI API 호출
   */
  private static async callOpenAI(prompt: string): Promise<string> {
    const apiKey = process.env.OPENAI_API_KEY;
    const payload = {
      model: "gpt-3.5-turbo",
      messages: [{ role: "user", content: prompt }],
      max_tokens: LLM_CONSTANTS.OPENAI_MAX_TOKENS,
      temperature: LLM_CONSTANTS.OPENAI_TEMPERATURE
    };
    
    const curlCommand = `curl -s https://api.openai.com/v1/chat/completions \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer ${apiKey}" \
      -d '${JSON.stringify(payload).replace(/'/g, "\\'")}'`;
    
    const { stdout } = await execAsync(curlCommand);
    const response = JSON.parse(stdout);
    
    if (response.choices && response.choices[0]) {
      return response.choices[0].message.content.trim();
    }
    
    throw new Error('Invalid OpenAI response');
  }

  /**
   * Anthropic API 호출
   */
  private static async callAnthropic(prompt: string): Promise<string> {
    const apiKey = process.env.ANTHROPIC_API_KEY;
    const payload = {
      model: "claude-3-haiku-20240307",
      max_tokens: LLM_CONSTANTS.ANTHROPIC_MAX_TOKENS,
      messages: [{ role: "user", content: prompt }],
      temperature: LLM_CONSTANTS.ANTHROPIC_TEMPERATURE
    };
    
    const curlCommand = `curl -s https://api.anthropic.com/v1/messages \
      -H "Content-Type: application/json" \
      -H "x-api-key: ${apiKey}" \
      -H "anthropic-version: 2023-06-01" \
      -d '${JSON.stringify(payload).replace(/'/g, "\\'")}'`;
    
    const { stdout } = await execAsync(curlCommand);
    const response = JSON.parse(stdout);
    
    if (response.content && response.content[0]) {
      return response.content[0].text.trim();
    }
    
    throw new Error('Invalid Anthropic response');
  }
}
