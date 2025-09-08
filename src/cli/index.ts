#!/usr/bin/env node

import { Command } from 'commander';
import chalk from 'chalk';
import { GitHookManager } from '../core/git-hooks';
import { ConfigManager } from '../core/config';
import { HookHandlers } from '../core/hook-handlers';
import { CliUtils } from '../core/utils';
import { i18n } from '../core/i18n';
import { StoreManager } from '../core/store-manager';
import { LLMApiClient } from '../core/llm-api';
import { CliCollector } from '../collectors/cli';
import path from 'path';
import fs from 'fs';
import { execSync } from 'child_process';

const program = new Command();

program
  .name('sayu')
  .description('커밋에 "왜"를 남기는 개인 로컬 블랙박스')
  .version('0.1.0');

// init 명령어 (interactive)
program
  .command('init')
  .description('현재 레포지토리에 Sayu 초기화')
  .option('--no-interactive', '대화형 설정 건너뛰기')
  .action(async (options) => {
    try {
      const repoRoot = CliUtils.requireGitRepo();

      console.log(chalk.blue('🔧 Sayu 초기화 중...'));
      console.log(chalk.gray(`레포지토리: ${repoRoot}`));

      // Git 훅 설치
      const hookManager = new GitHookManager(repoRoot);
      hookManager.install();

      // 데이터베이스 초기화
      StoreManager.checkConnection();
      console.log(chalk.gray('데이터베이스 초기화 완료'));

      // CLI hook 설치
      try {
        const cliCollector = new CliCollector(repoRoot);
        cliCollector.installHook();
        console.log(chalk.gray('zsh CLI tracking hook 설치 완료'));
        console.log(chalk.yellow('⚠️  새 터미널 세션에서 활성화됩니다 (또는 source ~/.zshrc 실행)'));
      } catch (error) {
        console.warn(chalk.yellow('CLI hook 설치 실패:'), (error as Error).message);
      }

      // 기본 설정 파일 생성
      ConfigManager.createDefault(repoRoot);

      console.log(chalk.green('\n✅ Sayu 설치 완료!'));
      
      const availableAPIs = LLMApiClient.getAvailableAPIs();
      if (!availableAPIs.gemini && !availableAPIs.openai && !availableAPIs.anthropic) {
        console.log(chalk.yellow('\n⚠️  LLM API 키가 설정되지 않았습니다'));
        console.log(chalk.gray('\n.env 파일에 다음 중 하나를 추가하세요:'));
        console.log(chalk.gray('  GEMINI_API_KEY=your-key'));
        console.log(chalk.gray('  OPENAI_API_KEY=your-key'));
        console.log(chalk.gray('  ANTHROPIC_API_KEY=your-key'));
      } else {
        console.log(chalk.gray('\n🎉 모든 준비 완료! 커밋하면 AI 컨텍스트가 자동으로 추가됩니다.'));
      }
    } catch (error) {
      CliUtils.handleError('초기화', error);
    }
  });

// hook 명령어 (내부용)
program
  .command('hook')
  .argument('<type>', 'commit-msg 또는 post-commit')
  .argument('[file]', '커밋 메시지 파일 경로')
  .description('Git 훅에서 내부적으로 사용')
  .action(async (type, file) => {
    try {
      const repoRoot = GitHookManager.getRepoRoot();
      if (!repoRoot) {
        // 훅에서는 조용히 실패
        process.exit(0);
      }

      if (type === 'commit-msg' && file) {
        const { HookHandlers } = await import('../core/hook-handlers');
        await HookHandlers.handleCommitMsg(file);
      } else if (type === 'post-commit') {
        const { HookHandlers } = await import('../core/hook-handlers');
        await HookHandlers.handlePostCommit();
      }

      process.exit(0);
    } catch (error) {
      // 훅에서는 조용히 실패 (Fail-open)
      console.error('Hook error:', (error as Error).message);
      process.exit(0);
    }
  });

program.parse(process.argv);
