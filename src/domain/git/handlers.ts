import fs from 'fs';
import path from 'path';
import * as dotenv from 'dotenv';

import { GitHookManager } from './hooks';
import { GitInfo } from './info';
import { Event } from '../events/types';
import { EventStore } from '../events/store';
import { ClaudeCollector } from '../collectors/llm-claude';
import { CursorCollector } from '../collectors/llm-cursor';
import { CliCollector } from '../collectors/cli';
import { LLMSummaryGenerator } from '../summary/llm';
import { MinimalSummaryGenerator } from '../summary/minimal';
import { EventFilter } from '../summary/event-filter';
import { ConfigManager } from '../../infra/config/manager';
import { LLMApiClient } from '../../infra/api/llm';
import { i18n } from '../../i18n';
import { TIME_CONSTANTS } from '../../shared/constants';
import { ErrorHandler } from '../../shared/error-handler';

export class HookHandlers {
  static async handleCommitMsg(commitMsgFile: string): Promise<void> {
    try {
      const repoRoot = GitHookManager.getRepoRoot();
      if (!repoRoot) return;
      
      const envPath = path.join(repoRoot, '.env');
      if (fs.existsSync(envPath)) {
        dotenv.config({ path: envPath });
      }

      const configManager = new ConfigManager(repoRoot);
      const userConfig = configManager.getEffectiveConfig();
      if (!userConfig.commitTrailer) return;

      const checkStagedFiles = GitInfo.getStagedFiles();
      const checkHasChanges = GitInfo.hasActualChanges();
      
      if (checkStagedFiles.length === 0 && !checkHasChanges) {
        console.error(i18n().t('errors.emptyCommit'));
        console.error(i18n().t('errors.useAllowEmpty'));
        process.exit(1);
      }
      
      if (checkStagedFiles.length === 0 && checkHasChanges) {
        console.log(i18n().t('errors.noStagedButChanges'));
      }

      const llmEvents: Event[] = [];
      const now = Date.now();
      
      const store = new EventStore();
      const lastCommitTime = store.getLastCommitTime(repoRoot);
      
      const configLookback = TIME_CONSTANTS.DEFAULT_LOOKBACK_HOURS * 60 * 60 * 1000;
      const sinceMs = lastCommitTime || now - configLookback;
      store.close();
      
      const fullConfig = configManager.get();
      
      try {
        const claudeCollector = new ClaudeCollector(repoRoot);
        const claudeEvents = await claudeCollector.pullSince(sinceMs, now, fullConfig);
        const filteredClaudeEvents = EventFilter.filterHighValueEvents(claudeEvents);
        
        if (claudeEvents.length !== filteredClaudeEvents.length) {
          console.log(`[Sayu] Claude events filtered: ${claudeEvents.length} → ${filteredClaudeEvents.length} (smart filter)`);
        }
        
        llmEvents.push(...filteredClaudeEvents);
      } catch (error) {
        // Silently ignore if Claude not available
      }
      
      try {
        const cursorCollector = new CursorCollector(repoRoot);
        const cursorEvents = await cursorCollector.pullSince(sinceMs, now, fullConfig);
        llmEvents.push(...cursorEvents);
      } catch (error) {
        // Silently ignore if Cursor not available
      }
      
      try {
        const cliCollector = new CliCollector(repoRoot);
        const cliEvents = await cliCollector.pullSince(sinceMs, now, fullConfig);
        llmEvents.push(...cliEvents);
      } catch (error) {
        // Silently ignore if CLI not available
      }
      
      const stagedFiles = GitInfo.getStagedFiles();
      const diffStats = GitInfo.getDiffStats();
      
      let summary: string;
      
      console.log(`[Sayu] ${i18n().t('cli.apiKeysAvailable')}:`, LLMApiClient.getAvailableAPIs());
      console.log(`[Sayu] Collected ${llmEvents.length} ${i18n().t('cli.collectedEvents')}`);
      
      const availableAPIs = LLMApiClient.getAvailableAPIs();
      if (availableAPIs.gemini || availableAPIs.openai || availableAPIs.anthropic) {
        console.log(`[Sayu] ${i18n().t('cli.attemptingGeneration')}`);
        try {
          summary = await LLMSummaryGenerator.generate(llmEvents, stagedFiles, diffStats);
          console.log(`[Sayu] ${i18n().t('cli.generationSuccess')}`);
          console.log(`[Sayu] ${i18n().t('cli.summaryLength')} ${summary.length} characters`);
        } catch (error) {
          console.error('[Sayu] LLM API failed, trying again with simplified prompt:', error instanceof Error ? error.message : String(error));
          
          try {
            summary = await LLMSummaryGenerator.generateSimplified(llmEvents, stagedFiles, diffStats);
            console.log('[Sayu] Simplified LLM summary generated successfully');
          } catch (retryError) {
            console.error('[Sayu] All LLM attempts failed, using minimal summary');
            summary = MinimalSummaryGenerator.generate(llmEvents, stagedFiles, diffStats);
          }
        }
      } else {
        console.log('[Sayu] No API keys found, using minimal summary');
        summary = MinimalSummaryGenerator.generate(llmEvents, stagedFiles, diffStats);
      }
      
      if (summary) {
        const currentMsg = fs.readFileSync(commitMsgFile, 'utf-8');
        
        if (currentMsg.includes('AI-Context (sayu)')) {
          return;
        }
        
        const newMsg = currentMsg.trimEnd() + '\n\n' + summary;
        fs.writeFileSync(commitMsgFile, newMsg);
      }
      
      const commitEvent: Event = {
        id: `commit-${Date.now()}`,
        ts: now,
        source: 'git',
        kind: 'commit',
        repo: repoRoot,
        cwd: repoRoot,
        file: null,
        range: null,
        actor: 'user',
        text: fs.readFileSync(commitMsgFile, 'utf-8').split('\n')[0],
        url: null,
        meta: {
          filesCount: `${stagedFiles.length}`,
          llmContext: llmEvents.length > 0 ? 'true' : 'false'
        }
      };
      
      const store2 = new EventStore();
      store2.insert(commitEvent);
      store2.close();
      
    } catch (error) {
      ErrorHandler.handle(error, {
        operation: 'commit-msg-hook',
        recoverable: true,
        details: 'Error occurred during Sayu hook execution but commit continues'
      });
    }
  }

  static async handlePostCommit(): Promise<void> {
    try {
      console.log('Post-commit: Hook executed');
    } catch (error) {
      console.error('Sayu post-commit hook error:', error);
    }
  }
}