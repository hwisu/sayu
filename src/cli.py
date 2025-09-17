"""Command-line interface for Sayu."""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import click
from rich.console import Console

import subprocess
from .config import Config
from .core import Storage
from .collectors import ClaudeCodeCollector, GitCollector
from .engine import Summarizer, LLMProvider
from .visualizer import TimelineVisualizer


console = Console()


@click.group()
@click.version_option(version="1.1.0", prog_name="sayu")
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
        "default_provider": "openrouter",
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
@click.option("--last", type=int, help="Look back N hours (default: since last commit)")
@click.option("--since-commit", is_flag=True, default=True, help="Use last commit as reference point")
@click.option("--structured", is_flag=True, help="Use structured output format (requires SAYU_STRUCTURED_OUTPUT=true)")
def summarize(hours: int, engine: str, last: int, since_commit: bool, structured: bool):
    """Summarize events within timeframes."""
    config = Config()
    storage = Storage(config.db_path)
    visualizer = TimelineVisualizer()

    # Get timeframe
    timeframe_hours = hours or config.timeframe_hours
    timeframe = timedelta(hours=timeframe_hours)

    # Get events - default to since last commit
    if since_commit and not last:
        git_collector = GitCollector()

        # Get the last two commits to find the range
        try:
            result = subprocess.run(
                ["git", "log", "--pretty=format:%H|%ad", "--date=iso", "-2"],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    # Get time of second-to-last commit
                    second_commit_parts = lines[1].split('|')
                    if len(second_commit_parts) >= 2:
                        date_str = second_commit_parts[1]
                        if '+' in date_str:
                            date_str = date_str.split('+')[0].strip()
                        if ' ' in date_str:
                            date_str = date_str.replace(' ', 'T')
                        since = datetime.fromisoformat(date_str)
                        console.print(f"[dim]Summarizing events between last two commits (since {since.strftime('%Y-%m-%d %H:%M:%S')})[/dim]")
                    else:
                        # Fallback to last commit time
                        last_commit_time = git_collector._get_last_commit_time()
                        if last_commit_time:
                            since = last_commit_time
                            console.print(f"[dim]Summarizing events since last commit: {since.strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
                        else:
                            console.print("[yellow]No commits found, using last 24 hours[/yellow]")
                            since = datetime.now() - timedelta(hours=24)
                else:
                    # Only one commit, use its time
                    last_commit_time = git_collector._get_last_commit_time()
                    if last_commit_time:
                        since = last_commit_time
                        console.print(f"[dim]Summarizing events since last commit: {since.strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
                    else:
                        console.print("[yellow]No commits found, using last 24 hours[/yellow]")
                        since = datetime.now() - timedelta(hours=24)
            else:
                console.print("[yellow]No commits found, using last 24 hours[/yellow]")
                since = datetime.now() - timedelta(hours=24)
        except:
            console.print("[yellow]Error getting commit history, using last 24 hours[/yellow]")
            since = datetime.now() - timedelta(hours=24)
    else:
        # Use time-based approach
        hours_back = last or 24
        since = datetime.now() - timedelta(hours=hours_back)
        console.print(f"[dim]Summarizing events from last {hours_back} hours[/dim]")

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
            command=command,
            structured=structured
        )
    
    # Show results
    visualizer.show_summary_timeline(summaries)


@cli.command(name='summarize-since-last-commit')
@click.option("-e", "--engine", help="LLM engine command")
def summarize_since_last_commit(engine: str):
    """Summarize events since the last commit."""
    _summarize_since_last_commit_impl(engine)


@cli.command(name='sslc')
@click.option("-e", "--engine", help="LLM engine command")
def sslc(engine: str):
    """Summarize events since the last commit (short alias)."""
    _summarize_since_last_commit_impl(engine)


def _summarize_since_last_commit_impl(engine: str):
    """Implementation for summarize-since-last-commit."""
    config = Config()
    storage = Storage(config.db_path)
    visualizer = TimelineVisualizer()

    # Get last commit time
    git_collector = GitCollector()
    last_commit_time = git_collector._get_last_commit_time()

    if not last_commit_time:
        console.print("[yellow]No commits found in this repository[/yellow]")
        return

    console.print(f"[dim]Collecting events since last commit: {last_commit_time.strftime('%Y-%m-%d %H:%M:%S')}[/dim]")

    # Get events since last commit
    events = storage.get_events(since=last_commit_time)

    if not events:
        console.print("[yellow]No events found since last commit[/yellow]")
        return

    # Create summarizer
    if engine:
        summarizer = Summarizer(LLMProvider.CUSTOM)
        command = engine
    else:
        provider = LLMProvider(config.default_provider)
        summarizer = Summarizer(provider)
        command = None

    # Summarize all events since last commit
    with console.status("[bold green]Summarizing events since last commit..."):
        summary = summarizer.summarize_all(events, command=command)

    # Show results
    console.print(f"\n[bold]Summary since last commit ({len(events)} events):[/bold]")
    console.print(summary)


@cli.command()
@click.argument('commit_range', required=False)
@click.option("-e", "--engine", help="LLM engine command")
@click.option("--show-events", is_flag=True, help="Show events before summary")
def diff(commit_range: str, engine: str, show_events: bool):
    """Show events and summary between commits.
    
    Examples:
    sayu diff                    # Show events since last commit
    sayu diff HEAD~1..HEAD       # Show events between last 2 commits
    sayu diff abc123..def456     # Show events between specific commits
    """
    config = Config()
    storage = Storage(config.db_path)
    visualizer = TimelineVisualizer()
    
    # Initialize git collector
    git_collector = GitCollector()
    
    # Get commit range
    if not commit_range:
        # Default: since last commit
        last_commit_time = git_collector._get_last_commit_time()
        if not last_commit_time:
            console.print("[yellow]No commits found in this repository[/yellow]")
            return
        since_time = last_commit_time
        console.print(f"[dim]Collecting events since last commit: {since_time.strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
    else:
        # Parse commit range
        if '..' in commit_range:
            from_commit, to_commit = commit_range.split('..', 1)
            since_time = git_collector._get_commit_time(from_commit)
            until_time = git_collector._get_commit_time(to_commit)
            
            if not since_time:
                console.print(f"[red]Commit {from_commit} not found[/red]")
                return
            if not until_time:
                console.print(f"[red]Commit {to_commit} not found[/red]")
                return
                
            console.print(f"[dim]Collecting events between {from_commit} and {to_commit}[/dim]")
            console.print(f"[dim]Time range: {since_time.strftime('%Y-%m-%d %H:%M:%S')} - {until_time.strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
        else:
            # Single commit - show events since that commit
            since_time = git_collector._get_commit_time(commit_range)
            if not since_time:
                console.print(f"[red]Commit {commit_range} not found[/red]")
                return
            console.print(f"[dim]Collecting events since commit {commit_range}: {since_time.strftime('%Y-%m-%d %H:%M:%S')}[/dim]")
    
    # Get events in the range
    if 'until_time' in locals():
        events = storage.get_events(since=since_time, until=until_time)
    else:
        events = storage.get_events(since=since_time)
    
    if not events:
        console.print("[yellow]No events found in the specified range[/yellow]")
        return
    
    # Show events if requested
    if show_events:
        console.print(f"\n[bold]Events ({len(events)} total):[/bold]")
        visualizer.show_timeline(events)
    
    # Create summarizer
    if engine:
        summarizer = Summarizer(LLMProvider.CUSTOM)
        command = engine
    else:
        provider = LLMProvider(config.default_provider)
        summarizer = Summarizer(provider)
        command = None
    
    # Summarize events
    with console.status("[bold green]Summarizing events..."):
        summary = summarizer.summarize_all(events, command=command)
    
    # Show summary
    console.print(f"\n[bold]Summary ({len(events)} events):[/bold]")
    console.print(summary)


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
