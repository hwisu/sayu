import { Config } from './types';
export declare class ConfigManager {
    private static readonly CONFIG_FILE;
    private config;
    constructor(repoRoot: string);
    private loadConfig;
    get(): Config;
    save(repoRoot: string): void;
    static createDefault(repoRoot: string): void;
}
//# sourceMappingURL=config.d.ts.map