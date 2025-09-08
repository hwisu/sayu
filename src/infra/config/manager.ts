import fs from 'fs';
import path from 'path';
import yaml from 'js-yaml';
import { z } from 'zod';
import { Config } from '../../domain/events/types';
import { DEFAULT_SECURITY_MASKS } from '../../shared/constants';

// Simple configuration schema - minimal options that users can modify
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

  // Apply user settings + environment variable overrides
  getUserConfig(): UserConfig {
    const config = { ...this.userConfig };
    
    // Environment variable overrides
    if (process.env.SAYU_ENABLED === 'false') config.enabled = false;
    if (process.env.SAYU_LANG === 'en' || process.env.SAYU_LANG === 'ko') {
      config.language = process.env.SAYU_LANG;
    }
    if (process.env.SAYU_TRAILER === 'false') config.commitTrailer = false;
    
    return config;
  }

  // Return full Config for backward compatibility (mostly fixed default values)
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

  // SimpleConfig compatibility method
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
# AI automatically collects your development context

# Enable Sayu (set to false to disable)
enabled: true

# Language setting (ko: Korean, en: English)  
language: ko

# Add AI context to commit messages
commitTrailer: true

# Can also be configured via environment variables:
# SAYU_ENABLED=false
# SAYU_LANG=en  
# SAYU_TRAILER=false
#
# LLM API keys in .env file:
# GEMINI_API_KEY=your-key
# OPENAI_API_KEY=your-key
# ANTHROPIC_API_KEY=your-key
`;

    fs.writeFileSync(configPath, defaultConfig, 'utf-8');
    console.log(`Created config at ${configPath}`);
  }
}

// Alias for SimpleConfigManager replacement
export { ConfigManager as SimpleConfigManager };
export type { UserConfig as SimpleConfigType };
