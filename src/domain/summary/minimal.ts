import { Event } from '../events/types';
import { TEXT_CONSTANTS } from '../../shared/constants';

export class MinimalSummaryGenerator {
  static generate(llmEvents: Event[], stagedFiles: string[], diffStats: string): string {
    const lines: string[] = [];
    lines.push('---');
    lines.push('AI-Context (sayu)');
    
    if (stagedFiles.length > 0) {
      const fileList = stagedFiles.slice(0, TEXT_CONSTANTS.MAX_FILE_DISPLAY).join(', ');
      const more = stagedFiles.length > TEXT_CONSTANTS.MAX_FILE_DISPLAY ? ` (+${stagedFiles.length - TEXT_CONSTANTS.MAX_FILE_DISPLAY} more)` : '';
      lines.push(`Files: ${fileList}${more}`);
    }
    
    if (llmEvents.length > 0) {
      const tools = new Set(llmEvents.map(e => e.meta?.tool).filter(Boolean));
      const toolList = Array.from(tools).join(', ') || 'unknown';
      lines.push(`Events: ${llmEvents.length} LLM interactions (${toolList})`);
    } else {
      lines.push(`Events: Code changes only`);
    }
    
    lines.push('---');
    
    return lines.join('\n');
  }
}