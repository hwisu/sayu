#!/usr/bin/env node

import { Command } from 'commander';
import chalk from 'chalk';
import { GitHookManager } from '../core/git-hooks';
import { ConfigManager } from '../core/config';
import { EventStore } from '../core/database';
import path from 'path';
import fs from 'fs';

const program = new Command();

program
  .name('sayu')
  .description('커밋에 "왜"를 남기는 개인 로컬 블랙박스')
  .version('0.1.0');

// init 명령어
program
  .command('init')
  .description('현재 레포지토리에 Sayu 초기화')
  .action(async () => {
    try {
      // Git 레포 확인
      const repoRoot = GitHookManager.getRepoRoot();
      if (!repoRoot) {
        console.error(chalk.red('❌ Git 저장소가 아닙니다.'));
        process.exit(1);
      }

      console.log(chalk.blue('🔧 Sayu 초기화 중...'));
      console.log(chalk.gray(`레포지토리: ${repoRoot}`));

      // 설정 파일 생성
      ConfigManager.createDefault(repoRoot);

      // Git 훅 설치
      const hookManager = new GitHookManager(repoRoot);
      hookManager.install();

      // 데이터베이스 초기화
      const store = new EventStore();
      store.close();
      console.log(chalk.gray('데이터베이스 초기화 완료'));

      console.log(chalk.green('✅ Sayu 초기화 완료!'));
      console.log(chalk.gray('\n다음 단계:'));
      console.log(chalk.gray('1. .sayu.yml 파일을 편집하여 설정을 조정하세요'));
      console.log(chalk.gray('2. 커밋할 때 자동으로 컨텍스트가 수집됩니다'));
      console.log(chalk.gray('3. "sayu health"로 상태를 확인할 수 있습니다'));
    } catch (error) {
      console.error(chalk.red('❌ 초기화 실패:'), (error as Error).message);
      process.exit(1);
    }
  });

// preview 명령어
program
  .command('preview')
  .description('현재 스테이징된 변경사항에 대한 컨텍스트 미리보기')
  .action(async () => {
    try {
      const repoRoot = GitHookManager.getRepoRoot();
      if (!repoRoot) {
        console.error(chalk.red('❌ Git 저장소가 아닙니다.'));
        process.exit(1);
      }

      console.log(chalk.blue('🔍 컨텍스트 미리보기...'));
      
      // TODO: 실제 미리보기 로직 구현
      console.log(chalk.yellow('⚠️  미리보기 기능은 아직 구현 중입니다.'));
    } catch (error) {
      console.error(chalk.red('❌ 미리보기 실패:'), (error as Error).message);
      process.exit(1);
    }
  });

// health 명령어
program
  .command('health')
  .description('Sayu 및 커넥터 상태 확인')
  .action(async () => {
    try {
      const repoRoot = GitHookManager.getRepoRoot();
      if (!repoRoot) {
        console.error(chalk.red('❌ Git 저장소가 아닙니다.'));
        process.exit(1);
      }

      console.log(chalk.blue('🏥 상태 확인 중...\n'));

      // Git 훅 상태
      const hooksDir = path.join(repoRoot, '.git', 'hooks');
      const commitMsgHook = path.join(hooksDir, 'commit-msg');
      const postCommitHook = path.join(hooksDir, 'post-commit');

      console.log(chalk.bold('Git Hooks:'));
      console.log(`  commit-msg: ${fs.existsSync(commitMsgHook) ? chalk.green('✓') : chalk.red('✗')} 설치됨`);
      console.log(`  post-commit: ${fs.existsSync(postCommitHook) ? chalk.green('✓') : chalk.red('✗')} 설치됨`);

      // 설정 파일 상태
      console.log(chalk.bold('\n설정:'));
      const configPath = path.join(repoRoot, '.sayu.yml');
      console.log(`  .sayu.yml: ${fs.existsSync(configPath) ? chalk.green('✓') : chalk.red('✗')} 존재함`);

      // 데이터베이스 상태
      console.log(chalk.bold('\n데이터베이스:'));
      try {
        const store = new EventStore();
        store.close();
        console.log(`  SQLite: ${chalk.green('✓')} 정상`);
      } catch (error) {
        console.log(`  SQLite: ${chalk.red('✗')} 오류 - ${(error as Error).message}`);
      }

      // TODO: 각 커넥터 상태 확인
      console.log(chalk.bold('\n커넥터:'));
      console.log(chalk.yellow('  ⚠️  커넥터 상태 확인은 구현 중입니다.'));

    } catch (error) {
      console.error(chalk.red('❌ 상태 확인 실패:'), (error as Error).message);
      process.exit(1);
    }
  });

// notes push 명령어
program
  .command('notes')
  .argument('<action>', 'push')
  .description('Git notes 관리')
  .action(async (action) => {
    try {
      if (action !== 'push') {
        console.error(chalk.red(`❌ 알 수 없는 액션: ${action}`));
        process.exit(1);
      }

      const repoRoot = GitHookManager.getRepoRoot();
      if (!repoRoot) {
        console.error(chalk.red('❌ Git 저장소가 아닙니다.'));
        process.exit(1);
      }

      console.log(chalk.blue('📝 Git notes 업데이트 중...'));
      
      // TODO: 실제 notes 업데이트 로직 구현
      console.log(chalk.yellow('⚠️  Notes 기능은 아직 구현 중입니다.'));
    } catch (error) {
      console.error(chalk.red('❌ Notes 업데이트 실패:'), (error as Error).message);
      process.exit(1);
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