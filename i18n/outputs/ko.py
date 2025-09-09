"""Korean output templates for Sayu"""

ko_outputs = {
    # Git trailer related
    'trailer_header': 'AI-Context (sayu)',
    'trailer_labels': {
        'intent': 'Intent:',
        'what_changed': 'Changes:',
        'conversation_flow': 'Context:'
    },

    # CLI messages
    'cli': {
        'initializing': '🔧 Sayu 초기화 중...',
        'repository': '레포지토리',
        'config_exists': '설정 파일이 이미 존재합니다',
        'hook_already_installed': 'Sayu 훅이 이미 설치되어 있습니다',
        'database_initialized': '데이터베이스 초기화 완료',
        'zsh_hook_installed': 'zsh CLI tracking hook 설치 완료',
        'new_terminal_required': '⚠️  새 터미널 세션에서 활성화됩니다 (또는 source ~/.zshrc 실행)',
        'init_complete': '✅ Sayu 초기화 완료!',
        'next_steps': '다음 단계:',
        'edit_config': '.sayu.yml 파일을 편집하여 설정을 조정하세요',
        'cli_tracking': '새 터미널에서 CLI 명령어가 자동으로 추적됩니다',
        'auto_commit': '커밋할 때 자동으로 컨텍스트가 수집됩니다',
        'check_health': '"sayu health"로 상태를 확인할 수 있습니다',
        
        # Health check messages
        'health_checking': '🏥 상태 확인 중...',
        'git_hooks': 'Git Hooks:',
        'installed': '설치됨',
        'config': '설정:',
        'exists': '존재함',
        'database': '데이터베이스:',
        'normal': '정상',
        'connection_failed': '연결 실패',
        'connectors': '커넥터:',
        'active': '활성',
        'log_file_not_found': '로그 파일 없음',
        'db_file_exists': 'DB 파일 존재',
        
        # Preview related
        'preview_context': '🔍 컨텍스트 미리보기...',
        'generated_trailer': '생성될 트레일러:',
        'no_context': '수집된 컨텍스트가 없습니다.',
        
        # API related
        'api_keys_available': 'API Keys available:',
        'collected_events': 'LLM events for context generation',
        'attempting_generation': 'Attempting LLM summary generation...',
        'generation_success': 'LLM summary generated successfully',
        'generation_failed': 'LLM API failed, trying again with simplified prompt:',
        'all_attempts_failed': 'All LLM attempts failed, using minimal summary',
        'no_api_keys': 'No API keys found, using minimal summary',
        'summary_length': 'Summary length:'
    },

    # Error messages
    'errors': {
        'empty_commit': '❌ Sayu: Empty commit rejected - no files staged and no changes detected',
        'use_allow_empty': '   Use --allow-empty if you intend to create an empty commit',
        'no_staged_but_changes': '⚠️  Sayu: No files staged but changes detected - allowing (likely configuration change)'
    }
}
