"""English output templates for Sayu"""

en_outputs = {
    # Git trailer related
    'trailer_header': 'AI-Context (sayu)',
    'trailer_labels': {
        'intent': 'Intent:',
        'changes': 'Changes:',
        'context': 'Context:'
    },

    # CLI messages
    'cli': {
        'initializing': '🔧 Initializing Sayu...',
        'repository': 'Repository',
        'config_exists': 'Config file already exists',
        'hook_already_installed': 'Sayu hook already installed',
        'database_initialized': 'Database initialization completed',
        'zsh_hook_installed': 'zsh CLI tracking hook installed',
        'new_terminal_required': '⚠️  Will be activated in new terminal sessions (or run source ~/.zshrc)',
        'init_complete': '✅ Sayu initialization completed!',
        'next_steps': 'Next steps:',
        'edit_config': 'Edit .sayu.yml file to adjust settings',
        'cli_tracking': 'CLI commands will be automatically tracked in new terminals',
        'auto_commit': 'Context will be automatically collected when committing',
        'check_health': 'Check status with "sayu health"',
        
        # Health check messages
        'health_checking': '🏥 Checking status...',
        'git_hooks': 'Git Hooks:',
        'installed': 'installed',
        'config': 'Config:',
        'exists': 'exists',
        'database': 'Database:',
        'normal': 'normal',
        'connection_failed': 'connection failed',
        'connectors': 'Connectors:',
        'active': 'active',
        'log_file_not_found': 'log file not found',
        'db_file_exists': 'DB file exists',
        
        # Preview related
        'preview_context': '🔍 Context preview...',
        'generated_trailer': 'Generated trailer:',
        'no_context': 'No context collected.',
        
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
