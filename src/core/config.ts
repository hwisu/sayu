import fs from 'fs';
import path from 'path';
import yaml from 'js-yaml';
import { z } from 'zod';
import { Config } from './types';
import { DEFAULT_SECURITY_MASKS } from './constants';

// 간단한 설정 스키마 - 사용자가 변경할 수 있는 최소한의 옵션
export const UserConfigSchema = z.object({
  enabled: z.boolean().default(true),
  language: z.enum(['ko', 'en']).default('ko'), 
  commitTrailer: z.boolean().default(true)
});

export type UserConfig = z.infer<typeof UserConfigSchema>;

export class ConfigManager {
  private static readonly CONFIG_FILE = '.sayu.yml';
  private userConfig: UserConfig;

  constructor(repoRoot: string) {
    this.userConfig = this.loadUserConfig(repoRoot);
  }

  private loadUserConfig(repoRoot: string): UserConfig {
    const configPath = path.join(repoRoot, ConfigManager.CONFIG_FILE);
    
    let rawConfig = {};
    
    if (fs.existsSync(configPath)) {
      try {
        const content = fs.readFileSync(configPath, 'utf-8');
        rawConfig = yaml.load(content) || {};
      } catch (error) {
        console.warn(`Failed to load config:`, error);
      }
    }
    
    return UserConfigSchema.parse(rawConfig);
  }

  // 사용자 설정 + 환경변수 오버라이드 적용
  getUserConfig(): UserConfig {
    const config = { ...this.userConfig };
    
    // 환경변수 오버라이드
    if (process.env.SAYU_ENABLED === 'false') config.enabled = false;
    if (process.env.SAYU_LANG === 'en' || process.env.SAYU_LANG === 'ko') {
      config.language = process.env.SAYU_LANG;
    }
    if (process.env.SAYU_TRAILER === 'false') config.commitTrailer = false;
    
    return config;
  }

  // 기존 코드 호환성을 위한 전체 Config 반환 (대부분 고정된 기본값)
  get(): Config {
    const userConfig = this.getUserConfig();
    
    return {
      connectors: {
        claude: true,
        cursor: true, 
        editor: true,
        cli: { mode: 'zsh-preexec' },
        browser: { mode: 'off' }
      },
      window: { 
        beforeCommitHours: 24 
      },
      filter: {
        domainAllowlist: ['github.com', 'developer.mozilla.org', 'stackoverflow.com'],
        noise: { graceMinutes: 5, minScore: 0.6 }
      },
      summarizer: { 
        mode: 'hybrid', 
        maxLines: { commit: 12 } 
      },
      privacy: { 
        maskSecrets: true,
        masks: [...DEFAULT_SECURITY_MASKS] 
      },
      output: { 
        commitTrailer: userConfig.commitTrailer 
      }
    };
  }

  // SimpleConfig 호환 메소드
  getEffectiveConfig(): UserConfig {
    return this.getUserConfig();
  }

  save(repoRoot: string, newConfig: Partial<UserConfig>): void {
    this.userConfig = UserConfigSchema.parse({ ...this.userConfig, ...newConfig });
    
    const configPath = path.join(repoRoot, ConfigManager.CONFIG_FILE);
    const content = yaml.dump(this.userConfig, { 
      indent: 2,
      lineWidth: 120 
    });
    
    fs.writeFileSync(configPath, content, 'utf-8');
  }

  static createDefault(repoRoot: string): void {
    const configPath = path.join(repoRoot, ConfigManager.CONFIG_FILE);
    
    if (fs.existsSync(configPath)) {
      return;
    }

    const defaultConfig = `# Sayu Configuration
# AI가 당신의 개발 컨텍스트를 자동으로 수집합니다

# Sayu 활성화 (false로 설정하면 비활성화)
enabled: true

# 언어 설정 (ko: 한국어, en: English)  
language: ko

# 커밋 메시지에 AI 컨텍스트 추가
commitTrailer: true

# 환경변수로도 설정 가능:
# SAYU_ENABLED=false
# SAYU_LANG=en  
# SAYU_TRAILER=false
#
# LLM API 키는 .env 파일에:
# GEMINI_API_KEY=your-key
# OPENAI_API_KEY=your-key
# ANTHROPIC_API_KEY=your-key
`;

    fs.writeFileSync(configPath, defaultConfig, 'utf-8');
    console.log(`Created config at ${configPath}`);
  }
}

// SimpleConfigManager 대체를 위한 별칭
export { ConfigManager as SimpleConfigManager };
export type { UserConfig as SimpleConfigType };