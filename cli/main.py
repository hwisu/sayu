#!/usr/bin/env python3
"""Sayu CLI - AI-Powered Commit Context Tracker"""

import sys
import os
from pathlib import Path
import click

from domain.git.hooks import GitHookManager
from infra.config.manager import ConfigManager
from domain.git.handlers import HookHandlers
from shared.utils import CliUtils
from domain.events.store_manager import StoreManager
from infra.api.llm import LLMApiClient
from domain.collectors.cli import CliCollector
from i18n import i18n



@click.group()
@click.version_option(version='0.2.0', prog_name='sayu')
def cli():
    """Sayu - Automatically capture the 'why' behind your code changes"""
    pass


@cli.command()
@click.option('--no-interactive', is_flag=True, help='Skip interactive setup')
def init(no_interactive):
    """Initialize Sayu in current repository"""
    try:
        repo_root = CliUtils.require_git_repo()
        
        print("🔧 Initializing Sayu...")
        print(f"Repository: {repo_root}")
        
        # Install Git hooks
        hook_manager = GitHookManager(repo_root)
        hook_manager.install()
        
        # Initialize database
        StoreManager.check_connection()
        print("Database initialized")
        
        # Install CLI hook
        try:
            cli_collector = CliCollector(repo_root)
            cli_collector.install_hook()
            print("zsh CLI tracking hook installed")
            print("⚠️  Will be active in new terminal sessions (or run: source ~/.zshrc)")
        except Exception as e:
            print(f"CLI hook installation failed: {e}")
        
        # Create default config
        ConfigManager.create_default(repo_root)
        
        print("\n✅ Sayu installation complete!")
        
        # Check API keys
        available_apis = LLMApiClient.get_available_apis()
        if not available_apis['gemini']:
            print("\n⚠️  No LLM API keys configured")
            print("\nAdd this to your .env file:")
            print("  GEMINI_API_KEY=your-key")
        else:
            print("\n🎉 All set! AI context will be automatically added to your commits.")
            
    except Exception as error:
        CliUtils.handle_error('initialization', error)
        sys.exit(1)


@cli.command()
@click.argument('hook_type', type=click.Choice(['commit-msg', 'post-commit']))
@click.argument('file', required=False)
def hook(hook_type, file):
    """Internal command for Git hooks"""
    try:
        repo_root = GitHookManager.get_repo_root()
        if not repo_root:
            # Fail silently in hooks
            sys.exit(0)
        
        # Run handler
        if hook_type == 'commit-msg' and file:
            HookHandlers.handle_commit_msg(file)
        elif hook_type == 'post-commit':
            HookHandlers.handle_post_commit()
        
        sys.exit(0)
    except Exception as error:
        # Fail-open: Don't block commits on errors
        print(f"Hook error: {error}", file=sys.stderr)
        sys.exit(0)


@cli.command()
def health():
    """Check Sayu system health"""
    try:
        repo_root = CliUtils.require_git_repo()
        
        print("\n🏥 Sayu Health Check\n" + "="*30)
        
        # Check Git hooks
        hook_manager = GitHookManager(repo_root)
        hooks_installed = hook_manager.check_installed()
        
        if hooks_installed:
            print("✅ Git hooks installed")
        else:
            print("❌ Git hooks not installed")
        
        # Check database
        try:
            StoreManager.check_connection()
            print("✅ Database connected")
        except:
            print("❌ Database connection failed")
        
        # Check collectors
        try:
            from domain.collectors.manager import CollectorManager
            collector_manager = CollectorManager(repo_root)
            collector_health = collector_manager.health_check()
            
            if collector_health['cursor']['ok']:
                cursor_info = collector_health['cursor']
                print(f"✅ Cursor connected ({cursor_info.get('conversations', 0)} conversations)")
            else:
                print(f"⚠️  Cursor: {collector_health['cursor']['reason']}")

            if collector_health['claude']['ok']:
                claude_info = collector_health['claude']
                print(f"✅ Claude connected ({claude_info.get('conversations', 0)} conversations)")
            else:
                print(f"⚠️  Claude: {collector_health['claude']['reason']}")
                
        except Exception as e:
            print(f"⚠️  Collector error: {e}")
        
        # Check API keys
        available_apis = LLMApiClient.get_available_apis()
        if available_apis['gemini']:
            print("✅ Gemini API configured")
        else:
            print("⚠️  No LLM API keys configured")
        
        # Check config
        try:
            config_manager = ConfigManager(repo_root)
            config = config_manager.get_user_config()
            print(f"✅ Config loaded (language: {config.language})")
        except:
            print("❌ Config loading failed")
            
    except Exception as error:
        CliUtils.handle_error('health check', error)
        sys.exit(1)


@cli.command()
def preview():
    """Preview AI context for current changes"""
    try:
        repo_root = CliUtils.require_git_repo()
        
        print("🔍 Previewing AI context...")
        
        # This would run the same logic as commit-msg hook
        # but display the result instead of modifying commit
        HookHandlers.preview_context(repo_root)
        
    except Exception as error:
        CliUtils.handle_error('preview', error)
        sys.exit(1)


@cli.group()
def collector():
    """Manage event collectors"""
    pass


@collector.command('cli-install')
def cli_install():
    """Install CLI tracking hook"""
    try:
        repo_root = CliUtils.require_git_repo()
        cli_collector = CliCollector(repo_root)
        cli_collector.install_hook()
        print("✅ CLI tracking hook installed")
        print("Run 'source ~/.zshrc' to activate")
    except Exception as error:
        CliUtils.handle_error('CLI install', error)
        sys.exit(1)


@collector.command('cli-uninstall')
def cli_uninstall():
    """Uninstall CLI tracking hook"""
    try:
        repo_root = CliUtils.require_git_repo()
        cli_collector = CliCollector(repo_root)
        cli_collector.uninstall_hook()
        print("✅ CLI tracking hook removed")
    except Exception as error:
        CliUtils.handle_error('CLI uninstall', error)
        sys.exit(1)


if __name__ == '__main__':
    cli()
