"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.ConfigManager = void 0;
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const js_yaml_1 = __importDefault(require("js-yaml"));
const types_1 = require("./types");
const zod_1 = require("zod");
class ConfigManager {
    static CONFIG_FILE = '.sayu.yml';
    config;
    constructor(repoRoot) {
        this.config = this.loadConfig(repoRoot);
    }
    loadConfig(repoRoot) {
        const configPath = path_1.default.join(repoRoot, ConfigManager.CONFIG_FILE);
        // 기본 설정
        let rawConfig = {};
        // 파일이 있으면 읽기
        if (fs_1.default.existsSync(configPath)) {
            try {
                const content = fs_1.default.readFileSync(configPath, 'utf-8');
                rawConfig = js_yaml_1.default.load(content) || {};
            }
            catch (error) {
                console.warn(`Failed to load config from ${configPath}:`, error);
            }
        }
        // 파싱 및 검증
        try {
            return types_1.Config.parse(rawConfig);
        }
        catch (error) {
            if (error instanceof zod_1.z.ZodError) {
                console.warn('Config validation errors:', error.errors);
            }
            // 기본값 반환
            return types_1.Config.parse({});
        }
    }
    get() {
        return this.config;
    }
    save(repoRoot) {
        const configPath = path_1.default.join(repoRoot, ConfigManager.CONFIG_FILE);
        const content = js_yaml_1.default.dump(this.config, {
            indent: 2,
            lineWidth: 120
        });
        fs_1.default.writeFileSync(configPath, content, 'utf-8');
    }
    static createDefault(repoRoot) {
        const configPath = path_1.default.join(repoRoot, ConfigManager.CONFIG_FILE);
        if (fs_1.default.existsSync(configPath)) {
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
        fs_1.default.writeFileSync(configPath, defaultConfig, 'utf-8');
        console.log(`Created default config at ${configPath}`);
    }
}
exports.ConfigManager = ConfigManager;
//# sourceMappingURL=config.js.map