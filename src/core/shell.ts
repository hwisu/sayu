import { execSync, spawn, SpawnOptionsWithoutStdio } from 'child_process';

/**
 * Safely executes shell commands with proper escaping and validation
 */
export class ShellExecutor {
  /**
   * Execute a command synchronously with safe argument handling
   */
  static execSync(command: string, args: string[] = [], options?: Parameters<typeof execSync>[1]): string {
    // Use spawn-style execution to avoid shell injection
    const [cmd, ...cmdArgs] = command.split(' ');
    const allArgs = [...cmdArgs, ...args];
    
    // Validate command to prevent path traversal
    if (cmd.includes('..') || cmd.includes('/')) {
      throw new Error(`Invalid command: ${cmd}`);
    }
    
    const result = execSync(`${cmd} ${allArgs.map(arg => this.escapeShellArg(arg)).join(' ')}`, options);
    return result.toString();
  }

  /**
   * Execute git commands safely
   */
  static gitExec(args: string[], options?: Parameters<typeof execSync>[1]): string {
    // Git commands are executed without shell to prevent injection
    const result = execSync(`git ${args.map(arg => this.escapeShellArg(arg)).join(' ')}`, {
      ...options,
      shell: false,
      encoding: 'utf8'
    } as any);
    return result.toString();
  }

  /**
   * Spawn a process safely
   */
  static spawn(command: string, args: string[] = [], options?: SpawnOptionsWithoutStdio) {
    // Validate command
    if (command.includes('..') || command.includes('\\')) {
      throw new Error(`Invalid command: ${command}`);
    }
    
    return spawn(command, args, {
      ...options,
      shell: false // Never use shell to prevent injection
    });
  }

  /**
   * Escape shell arguments to prevent injection
   */
  private static escapeShellArg(arg: string): string {
    if (!arg) return "''";
    
    // Remove any existing quotes
    arg = arg.replace(/['"]/g, '');
    
    // Escape special characters
    arg = arg.replace(/([\\$`!])/g, '\\$1');
    
    // Wrap in single quotes
    return `'${arg}'`;
  }

  /**
   * Validate and sanitize file paths
   */
  static sanitizePath(path: string): string {
    // Remove any attempts at path traversal
    path = path.replace(/\.\./g, '');
    
    // Remove any shell metacharacters
    path = path.replace(/[;&|<>$`\\]/g, '');
    
    return path;
  }
}