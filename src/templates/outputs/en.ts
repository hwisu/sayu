export const enOutputs = {
  // Git trailer related
  trailerHeader: 'AI-Context (sayu)',
  trailerLabels: {
    intent: 'Intent:',
    changes: 'Changes:',
    context: 'Context:'
  },

  // CLI messages
  cli: {
    initializing: '🔧 Initializing Sayu...',
    repository: 'Repository',
    configExists: 'Config file already exists',
    hookAlreadyInstalled: 'Sayu hook already installed',
    databaseInitialized: 'Database initialization completed',
    zshHookInstalled: 'zsh CLI tracking hook installed',
    newTerminalRequired: '⚠️  Will be activated in new terminal sessions (or run source ~/.zshrc)',
    initComplete: '✅ Sayu initialization completed!',
    nextSteps: 'Next steps:',
    editConfig: 'Edit .sayu.yml file to adjust settings',
    cliTracking: 'CLI commands will be automatically tracked in new terminals',
    autoCommit: 'Context will be automatically collected when committing',
    checkHealth: 'Check status with "sayu health"',
    
    // Health check messages
    healthChecking: '🏥 Checking status...',
    gitHooks: 'Git Hooks:',
    installed: 'installed',
    config: 'Config:',
    exists: 'exists',
    database: 'Database:',
    normal: 'normal',
    connectionFailed: 'connection failed',
    connectors: 'Connectors:',
    active: 'active',
    logFileNotFound: 'log file not found',
    dbFileExists: 'DB file exists',
    
    // Preview related
    previewContext: '🔍 Context preview...',
    generatedTrailer: 'Generated trailer:',
    noContext: 'No context collected.',
    
    // API related
    apiKeysAvailable: 'API Keys available:',
    collectedEvents: 'LLM events for context generation',
    attemptingGeneration: 'Attempting LLM summary generation...',
    generationSuccess: 'LLM summary generated successfully',
    generationFailed: 'LLM API failed, trying again with simplified prompt:',
    allAttemptsFailed: 'All LLM attempts failed, using minimal summary',
    noApiKeys: 'No API keys found, using minimal summary',
    summaryLength: 'Summary length:'
  },

  // Error messages
  errors: {
    emptyCommit: '❌ Sayu: Empty commit rejected - no files staged and no changes detected',
    useAllowEmpty: '   Use --allow-empty if you intend to create an empty commit',
    noStagedButChanges: '⚠️  Sayu: No files staged but changes detected - allowing (likely configuration change)'
  }
};
