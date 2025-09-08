export const koOutputs = {
  // Git trailer 관련
  trailerHeader: 'AI-Context (sayu)',
  trailerLabels: {
    intent: 'Intent:',
    changes: 'Changes:',
    context: 'Context:'
  },

  // CLI 메시지들
  cli: {
    initializing: '🔧 Sayu 초기화 중...',
    repository: '레포지토리',
    configExists: '설정 파일이 이미 존재합니다',
    hookAlreadyInstalled: 'Sayu 훅이 이미 설치되어 있습니다',
    databaseInitialized: '데이터베이스 초기화 완료',
    zshHookInstalled: 'zsh CLI tracking hook 설치 완료',
    newTerminalRequired: '⚠️  새 터미널 세션에서 활성화됩니다 (또는 source ~/.zshrc 실행)',
    initComplete: '✅ Sayu 초기화 완료!',
    nextSteps: '다음 단계:',
    editConfig: '.sayu.yml 파일을 편집하여 설정을 조정하세요',
    cliTracking: '새 터미널에서 CLI 명령어가 자동으로 추적됩니다',
    autoCommit: '커밋할 때 자동으로 컨텍스트가 수집됩니다',
    checkHealth: '"sayu health"로 상태를 확인할 수 있습니다',
    
    // Health check 메시지들
    healthChecking: '🏥 상태 확인 중...',
    gitHooks: 'Git Hooks:',
    installed: '설치됨',
    config: '설정:',
    exists: '존재함',
    database: '데이터베이스:',
    normal: '정상',
    connectionFailed: '연결 실패',
    connectors: '커넥터:',
    active: '활성',
    logFileNotFound: '로그 파일 없음',
    dbFileExists: 'DB 파일 존재',
    
    // 미리보기 관련
    previewContext: '🔍 컨텍스트 미리보기...',
    generatedTrailer: '생성될 트레일러:',
    noContext: '수집된 컨텍스트가 없습니다.',
    
    // API 관련
    apiKeysAvailable: 'API Keys available:',
    collectedEvents: 'LLM events for context generation',
    attemptingGeneration: 'Attempting LLM summary generation...',
    generationSuccess: 'LLM summary generated successfully',
    generationFailed: 'LLM API failed, trying again with simplified prompt:',
    allAttemptsFailed: 'All LLM attempts failed, using minimal summary',
    noApiKeys: 'No API keys found, using minimal summary',
    summaryLength: 'Summary length:'
  },

  // 에러 메시지들
  errors: {
    emptyCommit: '❌ Sayu: Empty commit rejected - no files staged and no changes detected',
    useAllowEmpty: '   Use --allow-empty if you intend to create an empty commit',
    noStagedButChanges: '⚠️  Sayu: No files staged but changes detected - allowing (likely configuration change)'
  }
};
