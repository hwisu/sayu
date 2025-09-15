"""Command-line interface for Sayu."""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import click
from rich.console import Console

from .config import Config
from .core import Storage
from .collectors import ClaudeCodeCollector, GitCollector
from .engine import Summarizer, LLMProvider
from .visualizer import TimelineVisualizer


console = Console()


@click.group()
@click.version_option(version="1.0.0", prog_name="sayu")
def cli():
    """AI conversation history tracker with timeline visualization."""
    pass


@cli.command()
def init():
    """Initialize Sayu in the current directory."""
    config = Config()
    
    # Create config file
    config.data = {
        "db_path": str(Path.home() / ".sayu" / "events.db"),
        "default_provider": "gemini",
        "timeframe_hours": 2,
        "collectors": {
            "claude-code": {
                "enabled": True
            },
            "git": {
                "enabled": True
            }
        }
    }
    config.save()
    
    # Set up collectors
    claude_collector = ClaudeCodeCollector()
    claude_collector.setup()
    
    git_collector = GitCollector()
    git_collector.setup()
    
    console.print("[green]✓[/green] Initialized Sayu")
    console.print(f"[dim]Config: {config.config_path}[/dim]")
    console.print(f"[dim]Database: {config.db_path}[/dim]")


@cli.command()
def collect():
    """Manually collect events from all sources."""
    config = Config()
    storage = Storage(config.db_path)
    
    # Get latest timestamp
    latest = storage.get_latest_timestamp()
    
    # Collect from all enabled sources
    total_events = 0
    
    if config.get_collector_config("claude-code").get("enabled", True):
        collector = ClaudeCodeCollector()
        events = collector.collect(since=latest)
        if events:
            storage.add_events(events)
            total_events += len(events)
            console.print(f"[green]✓[/green] Collected {len(events)} events from claude-code")
    
    if config.get_collector_config("git").get("enabled", True):
        git_collector = GitCollector()
        events = git_collector.collect(since=latest)
        if events:
            storage.add_events(events)
            total_events += len(events)
            console.print(f"[green]✓[/green] Collected {len(events)} events from git")
    
    if total_events == 0:
        console.print("[yellow]No new events collected[/yellow]")
    else:
        console.print(f"[green]Total: {total_events} events[/green]")


@cli.command()
@click.option("-n", "--last", type=int, default=10, help="Number of events to show")
@click.option("-s", "--source", help="Filter by source")
@click.option("-v", "--verbose", is_flag=True, help="Show full content")
def timeline(last: int, source: str, verbose: bool):
    """Show event timeline."""
    config = Config()
    storage = Storage(config.db_path)
    visualizer = TimelineVisualizer()
    
    # Get events
    events = storage.get_events(source=source, limit=last)
    
    # Show timeline
    visualizer.show_timeline(events, show_content=verbose)
    
    # Show stats
    if verbose:
        visualizer.show_stats(events)


@cli.command()
@click.option("-h", "--hours", type=int, help="Timeframe in hours")
@click.option("-e", "--engine", help="LLM engine command")
@click.option("--last", type=int, default=24, help="Look back N hours")
def summarize(hours: int, engine: str, last: int):
    """Summarize events within timeframes."""
    config = Config()
    storage = Storage(config.db_path)
    visualizer = TimelineVisualizer()
    
    # Get timeframe
    timeframe_hours = hours or config.timeframe_hours
    timeframe = timedelta(hours=timeframe_hours)
    
    # Get events from last N hours
    since = datetime.now() - timedelta(hours=last)
    events = storage.get_events(since=since)
    
    if not events:
        console.print("[yellow]No events to summarize[/yellow]")
        return
    
    # Create summarizer
    if engine:
        summarizer = Summarizer(LLMProvider.CUSTOM)
        command = engine
    else:
        provider = LLMProvider(config.default_provider)
        summarizer = Summarizer(provider)
        command = None
    
    # Summarize
    with console.status("[bold green]Summarizing events..."):
        summaries = summarizer.summarize_timeframe(
            events,
            timeframe,
            command=command
        )
    
    # Show results
    visualizer.show_summary_timeline(summaries)


@cli.command()
def watch():
    """Watch for new events in real-time."""
    config = Config()
    storage = Storage(config.db_path)
    visualizer = TimelineVisualizer()
    
    console.print("[green]Watching for new events...[/green]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")
    
    try:
        import time
        last_check = storage.get_latest_timestamp() or datetime.now()
        
        while True:
            # Collect new events
            collector = ClaudeCodeCollector()
            events = collector.collect(since=last_check)
            
            if events:
                # Store events
                storage.add_events(events)
                
                # Show new events
                console.print(f"\n[green]New events ({len(events)}):[/green]")
                visualizer.show_timeline(events)
                
                # Update last check
                last_check = max(e.timestamp for e in events)
            
            time.sleep(5)  # Check every 5 seconds
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped watching[/yellow]")


@cli.command()
def stats():
    """Show statistics about collected events."""
    config = Config()
    storage = Storage(config.db_path)
    visualizer = TimelineVisualizer()
    
    # Get all events
    events = storage.get_events()
    
    if not events:
        console.print("[yellow]No events collected yet[/yellow]")
        return
    
    visualizer.show_stats(events)


@cli.command()
def git_hook():
    """Set up git hooks for automatic commit integration."""
    config = Config()
    
    # Create post-commit hook
    git_dir = Path(".git")
    if not git_dir.exists():
        console.print("[red]Not a git repository[/red]")
        return
    
    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    
    post_commit_hook = hooks_dir / "post-commit"
    post_commit_hook.write_text('''#!/bin/sh
# Sayu post-commit hook
sayu collect >/dev/null 2>&1 || true
''')
    post_commit_hook.chmod(0o755)
    
    console.print("[green]✓[/green] Git hooks installed")
    console.print("[dim]Will auto-collect events after each commit[/dim]")


@cli.command()
def clean():
    """Remove Sayu from the current directory."""
    config = Config()
    
    # Remove collector hooks
    claude_collector = ClaudeCodeCollector()
    claude_collector.teardown()
    
    git_collector = GitCollector()
    git_collector.teardown()
    
    # Remove config
    if config.config_path.exists():
        config.config_path.unlink()
    
    console.print("[green]✓[/green] Removed Sayu configuration")


def main():
    """Main entry point."""
    try:
        cli()
    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()