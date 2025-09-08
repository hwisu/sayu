# Sayu - AI-Powered Commit Context Tracker

> Automatically capture the "why" behind your code changes using LLM conversation history

## Purpose

Over time, the reasoning behind code changes gets lost. Sayu automatically analyzes your **Claude/Cursor LLM conversations** at commit time to record the **intent, approach, and context** of your changes in structured Korean summaries.

## Key Features

- **🤖 LLM Conversation Collection**: Auto-extract Claude and Cursor conversation logs
- **🧠 Smart Filtering**: Utility-based selection of important conversations (93% noise reduction)
- **🇰🇷 Korean Context**: LLM analyzes intent/changes/approach/context in Korean
- **🔍 Conversation Analysis**: Automatic detection of question patterns, problem-solving processes, and anomalies
- **🛡️ Empty Commit Validation**: Blocks meaningless commits while allowing configuration changes
- **🔐 Local-First**: All data stored locally (privacy protected)
- **⚡ Fail-Open**: Hook failures don't block commits

## Installation

```bash
# Install dependencies
npm install

# Build the project
npm run build

# Initialize Sayu in your repository
node dist/cli/index.js init
```

## Usage

### Initialize
```bash
# Run in your Git repository
sayu init
```

This command:
- Creates `.sayu.yml` configuration file
- Installs Git hooks (commit-msg, post-commit)
- Initializes local SQLite database (`~/.sayu/events.db`)

### Check Status
```bash
sayu health
```

### Commit
Commit as usual and LLM conversation analysis will be automatically added:

```bash
git add .
git commit -m "Fix authentication bug"
```

Result:
```
Fix authentication bug

---
AI-Context (sayu)
Intent: 사용자 인증 버그 수정을 통해 로그인 실패 문제 해결
Changes: auth.js의 토큰 검증 로직 수정, test/auth.test.js에 새로운 테스트 케이스 추가
Approach: JWT 디코딩 함수의 예외 처리를 개선하고 만료된 토큰 감지 로직 강화
Context: Claude와의 대화에서 토큰 만료 시 에러 처리 방식에 대한 논의와 테스트 케이스 작성 과정 포함
---
```

## Configuration (.sayu.yml)

```yaml
connectors:
  claude: true      # ✅ Collect Claude conversation logs (~/.claude/projects/)
  cursor: true      # ✅ Collect Cursor conversation DB (~/Library/Application Support/Cursor/)
  cli:              # ✅ Track CLI commands
    mode: "zsh-preexec"  # "zsh-preexec" | "atuin" | "off"
  git: true         # ✅ Collect Git events

window:
  beforeCommitHours: 168  # Time range to collect (one week, considering Friday→Monday gaps)

output:
  commitTrailer: true    # Add trailer to commit messages
  gitNotes: false       # Create git notes (planned)

privacy:
  maskSecrets: false     # Mask sensitive information
  masks: []             # Patterns to mask
```

## API Key Setup (.env)

Set one of these API keys for LLM summary generation:

```bash
# Gemini (recommended)
GEMINI_API_KEY=your_api_key_here

# Or OpenAI
OPENAI_API_KEY=your_api_key_here

# Or Anthropic
ANTHROPIC_API_KEY=your_api_key_here
```

## Architecture

```
[LLM Collectors] → [Smart Filter] → [LLM Analysis] → [Git Hooks]
       ↓                ↓              ↓              ↓
Claude/Cursor → Utility-based → Gemini/GPT/Claude → Commit Trailer
    Logs         Selection      Korean Summary      Intent/Changes/
                (93% reduction)   + Process        Approach/Context
                                 Analysis
```

### Processing Flow
1. **Collection**: Extract conversations from Claude JSONL, Cursor SQLite
2. **Filtering**: Remove low-utility events (tool usage, confirmation messages)
3. **Analysis**: LLM analyzes conversation patterns, problem-solving processes, anomalies
4. **Summary**: Generate structured Korean Intent/Changes/Approach/Context

## Project Structure

```
sayu/
├── src/
│   ├── core/           # Core modules
│   │   ├── types.ts              # Type definitions
│   │   ├── database.ts           # SQLite event store
│   │   ├── config.ts             # Configuration management
│   │   ├── git-hooks.ts          # Git hook management
│   │   ├── hook-handlers.ts      # 🔥 Main logic (LLM summary, filtering)
│   │   ├── collector-manager.ts  # Collector integration
│   │   └── utils.ts              # Utilities
│   ├── collectors/     # Event collectors
│   │   ├── git.ts               # Git events
│   │   ├── llm-claude.ts        # 🤖 Claude conversations (JSONL)
│   │   └── llm-cursor.ts        # 🤖 Cursor conversations (SQLite)
│   └── cli/           # CLI commands
│       └── index.ts             # CLI entry point
├── dist/              # Build output
├── .env               # API key configuration
└── .sayu.yml          # Project configuration
```

## Data Sources

### LLM Conversation Collection
- **Claude**: `~/.claude/projects/{repo}/` JSONL files
- **Cursor**: `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb`

### Local Database Storage
Events are stored in `~/.sayu/events.db`:

```sql
CREATE TABLE events (
  id TEXT PRIMARY KEY,
  ts INTEGER,           -- Timestamp
  source TEXT,          -- 'git', 'llm'
  kind TEXT,            -- 'commit', 'chat'
  repo TEXT,            -- Repository path
  cwd TEXT,             -- Working directory
  file TEXT,            -- Related file
  range TEXT,           -- Code range
  actor TEXT,           -- 'user', 'assistant'
  text TEXT,            -- Event content
  url TEXT,             -- URL (if available)
  meta TEXT             -- JSON metadata
);
```

## Testing

```bash
# Build
npm run build

# Preview current changes
sayu preview

# Check system status
sayu health

# CLI tracking management
sayu cli install    # Install zsh hook
sayu cli uninstall  # Remove zsh hook
```

## Roadmap

- [x] **Phase 1**: Core infrastructure (DB, Git hooks, config)
- [x] **Phase 2**: Git collector and rule-based summaries  
- [x] **Phase 3**: LLM collectors (Claude, Cursor) ✨
- [x] **Phase 4**: Intelligent LLM summaries (Gemini/GPT/Claude) ✨
- [x] **Phase 5**: Smart filtering & Korean responses ✨
- [x] **Phase 6**: Conversation analysis & anomaly detection ✨
- [ ] **Phase 7**: CLI/Editor collectors
- [ ] **Phase 8**: Browser activity collection
- [ ] **Phase 9**: Git notes integration

## Performance Features

- **93% noise reduction**: 1200 events → 80 core events filtering
- **Real-time processing**: LLM analysis completed within 2-3 seconds per commit
- **Memory efficient**: Limited to 2-hour range, prevents excessive data collection
- **Safe failure**: Falls back to simplified summaries on API failures

## Target Users

- Optimized for **macOS + Cursor + Claude** users
- Korean development teams/developers
- LLM-based development workflow users
- Teams that value commit history quality

## Contributing

PRs and issues are welcome!

## License

MIT
