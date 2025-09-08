import fs from 'fs';
import path from 'path';
import yaml from 'js-yaml';
import { Config } from './types';
import { z } from 'zod';

export class ConfigManager {
  private static readonly CONFIG_FILE = '.sayu.yml';
  private config: Config;

  constructor(repoRoot: string) {
    this.config = this.loadConfig(repoRoot);
  }

  private loadConfig(repoRoot: string): Config {
    const configPath = path.join(repoRoot, ConfigManager.CONFIG_FILE);
    
    // 기본 설정
    let rawConfig = {};
    
    // 파일이 있으면 읽기
    if (fs.existsSync(configPath)) {
      try {
        const content = fs.readFileSync(configPath, 'utf-8');
        rawConfig = yaml.load(content) || {};
      } catch (error) {
        console.warn(`Failed to load config from ${configPath}:`, error);
      }
    }
    
    // 파싱 및 검증
    try {
      return Config.parse(rawConfig);
    } catch (error) {
      if (error instanceof z.ZodError) {
        console.warn('Config validation errors:', error.errors);
      }
      // 기본값 반환
      return Config.parse({});
    }
  }

  get(): Config {
    return this.config;
  }

  save(repoRoot: string): void {
    const configPath = path.join(repoRoot, ConfigManager.CONFIG_FILE);
    const content = yaml.dump(this.config, { 
      indent: 2,
      lineWidth: 120 
    });
    
    fs.writeFileSync(configPath, content, 'utf-8');
  }

  static createDefault(repoRoot: string): void {
    const configPath = path.join(repoRoot, ConfigManager.CONFIG_FILE);
    
    if (fs.existsSync(configPath)) {
      console.log(`Config file already exists at ${configPath}`);
      return;
    }

    const defaultConfig = `# Sayu Configuration
# 커밋에 '왜'를 남기는 개인 로컬 블랙박스

connectors:
  claude: true
  cursor: true
  editor: true
  cli:
    mode: "zsh-preexec"   # or "atuin" | "off"
  browser:
    mode: "off"           # or "extension" | "activitywatch"

window:
  beforeCommitHours: 24    # 커밋 전 몇 시간의 이벤트를 수집할지

filter:
  domainAllowlist:
    - "github.com"
    - "developer.mozilla.org"
    - "stackoverflow.com"
  noise:
    graceMinutes: 5       # 커밋 전후 여유 시간
    minScore: 0.6         # 최소 관련성 점수

summarizer:
  mode: "hybrid"          # "rules" | "llm" | "hybrid"
  maxLines:
    commit: 12            # 커밋 메시지 트레일러 최대 줄 수
    notes: 25             # git notes 최대 줄 수

privacy:
  maskSecrets: true       # 민감정보 마스킹 여부
  masks:                  # 추가 마스킹 패턴 (정규식)
    - "AKIA[0-9A-Z]{16}"  # AWS Access Key
    - "(?i)authorization:\\\\s*Bearer\\\\s+[A-Za-z0-9._-]+"

output:
  commitTrailer: true     # 커밋 메시지에 트레일러 추가
  gitNotes: true          # git notes 생성
  notesRef: "refs/notes/sayu"
`;

    fs.writeFileSync(configPath, defaultConfig, 'utf-8');
    console.log(`Created default config at ${configPath}`);
  }
}