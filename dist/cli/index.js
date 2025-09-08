#!/usr/bin/env node
"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const commander_1 = require("commander");
const chalk_1 = __importDefault(require("chalk"));
const git_hooks_1 = require("../core/git-hooks");
const config_1 = require("../core/config");
const database_1 = require("../core/database");
const path_1 = __importDefault(require("path"));
const fs_1 = __importDefault(require("fs"));
const program = new commander_1.Command();
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
        const repoRoot = git_hooks_1.GitHookManager.getRepoRoot();
        if (!repoRoot) {
            console.error(chalk_1.default.red('❌ Git 저장소가 아닙니다.'));
            process.exit(1);
        }
        console.log(chalk_1.default.blue('🔧 Sayu 초기화 중...'));
        console.log(chalk_1.default.gray(`레포지토리: ${repoRoot}`));
        // 설정 파일 생성
        config_1.ConfigManager.createDefault(repoRoot);
        // Git 훅 설치
        const hookManager = new git_hooks_1.GitHookManager(repoRoot);
        hookManager.install();
        // 데이터베이스 초기화
        const store = new database_1.EventStore();
        store.close();
        console.log(chalk_1.default.gray('데이터베이스 초기화 완료'));
        console.log(chalk_1.default.green('✅ Sayu 초기화 완료!'));
        console.log(chalk_1.default.gray('\n다음 단계:'));
        console.log(chalk_1.default.gray('1. .sayu.yml 파일을 편집하여 설정을 조정하세요'));
        console.log(chalk_1.default.gray('2. 커밋할 때 자동으로 컨텍스트가 수집됩니다'));
        console.log(chalk_1.default.gray('3. "sayu health"로 상태를 확인할 수 있습니다'));
    }
    catch (error) {
        console.error(chalk_1.default.red('❌ 초기화 실패:'), error.message);
        process.exit(1);
    }
});
// preview 명령어
program
    .command('preview')
    .description('현재 스테이징된 변경사항에 대한 컨텍스트 미리보기')
    .action(async () => {
    try {
        const repoRoot = git_hooks_1.GitHookManager.getRepoRoot();
        if (!repoRoot) {
            console.error(chalk_1.default.red('❌ Git 저장소가 아닙니다.'));
            process.exit(1);
        }
        console.log(chalk_1.default.blue('🔍 컨텍스트 미리보기...'));
        // TODO: 실제 미리보기 로직 구현
        console.log(chalk_1.default.yellow('⚠️  미리보기 기능은 아직 구현 중입니다.'));
    }
    catch (error) {
        console.error(chalk_1.default.red('❌ 미리보기 실패:'), error.message);
        process.exit(1);
    }
});
// health 명령어
program
    .command('health')
    .description('Sayu 및 커넥터 상태 확인')
    .action(async () => {
    try {
        const repoRoot = git_hooks_1.GitHookManager.getRepoRoot();
        if (!repoRoot) {
            console.error(chalk_1.default.red('❌ Git 저장소가 아닙니다.'));
            process.exit(1);
        }
        console.log(chalk_1.default.blue('🏥 상태 확인 중...\n'));
        // Git 훅 상태
        const hooksDir = path_1.default.join(repoRoot, '.git', 'hooks');
        const commitMsgHook = path_1.default.join(hooksDir, 'commit-msg');
        const postCommitHook = path_1.default.join(hooksDir, 'post-commit');
        console.log(chalk_1.default.bold('Git Hooks:'));
        console.log(`  commit-msg: ${fs_1.default.existsSync(commitMsgHook) ? chalk_1.default.green('✓') : chalk_1.default.red('✗')} 설치됨`);
        console.log(`  post-commit: ${fs_1.default.existsSync(postCommitHook) ? chalk_1.default.green('✓') : chalk_1.default.red('✗')} 설치됨`);
        // 설정 파일 상태
        console.log(chalk_1.default.bold('\n설정:'));
        const configPath = path_1.default.join(repoRoot, '.sayu.yml');
        console.log(`  .sayu.yml: ${fs_1.default.existsSync(configPath) ? chalk_1.default.green('✓') : chalk_1.default.red('✗')} 존재함`);
        // 데이터베이스 상태
        console.log(chalk_1.default.bold('\n데이터베이스:'));
        try {
            const store = new database_1.EventStore();
            store.close();
            console.log(`  SQLite: ${chalk_1.default.green('✓')} 정상`);
        }
        catch (error) {
            console.log(`  SQLite: ${chalk_1.default.red('✗')} 오류 - ${error.message}`);
        }
        // TODO: 각 커넥터 상태 확인
        console.log(chalk_1.default.bold('\n커넥터:'));
        console.log(chalk_1.default.yellow('  ⚠️  커넥터 상태 확인은 구현 중입니다.'));
    }
    catch (error) {
        console.error(chalk_1.default.red('❌ 상태 확인 실패:'), error.message);
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
            console.error(chalk_1.default.red(`❌ 알 수 없는 액션: ${action}`));
            process.exit(1);
        }
        const repoRoot = git_hooks_1.GitHookManager.getRepoRoot();
        if (!repoRoot) {
            console.error(chalk_1.default.red('❌ Git 저장소가 아닙니다.'));
            process.exit(1);
        }
        console.log(chalk_1.default.blue('📝 Git notes 업데이트 중...'));
        // TODO: 실제 notes 업데이트 로직 구현
        console.log(chalk_1.default.yellow('⚠️  Notes 기능은 아직 구현 중입니다.'));
    }
    catch (error) {
        console.error(chalk_1.default.red('❌ Notes 업데이트 실패:'), error.message);
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
        const repoRoot = git_hooks_1.GitHookManager.getRepoRoot();
        if (!repoRoot) {
            // 훅에서는 조용히 실패
            process.exit(0);
        }
        if (type === 'commit-msg' && file) {
            const { HookHandlers } = await Promise.resolve().then(() => __importStar(require('../core/hook-handlers')));
            await HookHandlers.handleCommitMsg(file);
        }
        else if (type === 'post-commit') {
            const { HookHandlers } = await Promise.resolve().then(() => __importStar(require('../core/hook-handlers')));
            await HookHandlers.handlePostCommit();
        }
        process.exit(0);
    }
    catch (error) {
        // 훅에서는 조용히 실패 (Fail-open)
        console.error('Hook error:', error.message);
        process.exit(0);
    }
});
program.parse(process.argv);
//# sourceMappingURL=index.js.map