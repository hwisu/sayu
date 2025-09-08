import chalk from 'chalk';
import { i18n } from '../i18n';

export interface ErrorContext {
  operation: string;
  details?: string;
  suggestion?: string;
  recoverable?: boolean;
}

export class ErrorHandler {
  static handle(error: unknown, context: ErrorContext): void {
    const errorMessage = this.getErrorMessage(error);
    const userFriendlyMessage = this.getUserFriendlyMessage(errorMessage, context);
    
    if (context.recoverable) {
      console.warn(chalk.yellow('⚠️ ' + userFriendlyMessage));
    } else {
      console.error(chalk.red('❌ ' + userFriendlyMessage));
    }
    
    if (context.suggestion) {
      console.log(chalk.gray('💡 ' + context.suggestion));
    }
    
    // Only output detailed errors in debug mode
    if (process.env.SAYU_DEBUG === 'true') {
      console.error(chalk.gray('\n[Debug] Original error:'));
      console.error(error);
    }
  }
  
  private static getErrorMessage(error: unknown): string {
    if (error instanceof Error) {
      return error.message;
    }
    return String(error);
  }
  
  private static getUserFriendlyMessage(errorMessage: string, context: ErrorContext): string {
    const outputs = i18n().getOutputs();
    
    // Match common error patterns
    if (errorMessage.includes('ENOENT')) {
      return `File not found during ${context.operation}`;
    }
    
    if (errorMessage.includes('EACCES') || errorMessage.includes('Permission denied')) {
      return `Permission denied during ${context.operation}`;
    }
    
    if (errorMessage.includes('SQLITE')) {
      return `Database error during ${context.operation}`;
    }
    
    if (errorMessage.includes('API') || errorMessage.includes('fetch')) {
      return `API error during ${context.operation}`;
    }
    
    // Operation-specific errors
    if (context.operation === 'git-hook-install') {
      return 'Failed to install git hooks';
    }
    
    if (context.operation === 'llm-collection') {
      return 'Failed to collect LLM data';
    }
    
    // Default error message
    return context.details || `Error during ${context.operation}: ${errorMessage}`;
  }
  
  static async tryWithFallback<T>(
    operation: () => Promise<T>,
    fallback: T,
    context: ErrorContext
  ): Promise<T> {
    try {
      return await operation();
    } catch (error) {
      this.handle(error, { ...context, recoverable: true });
      return fallback;
    }
  }
}
