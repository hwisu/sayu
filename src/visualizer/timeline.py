"""Timeline visualization for events."""

from rich.console import Console
from rich.table import Table

from ..core import Event


class TimelineVisualizer:
    """Visualize events as a timeline."""

    def __init__(self):
        """Initialize visualizer."""
        self.console = Console()

    def show_timeline(self, events: list[Event], show_content: bool = False) -> None:
        """
        Display events as a timeline.

        Args:
            events: List of events to display
            show_content: Whether to show full content
        """
        if not events:
            self.console.print("[yellow]No events to display[/yellow]")
            return

        # Sort events by timestamp (make all timezone-naive for comparison)
        def get_naive_timestamp(event):
            timestamp = event.timestamp
            if timestamp.tzinfo is not None:
                return timestamp.replace(tzinfo=None)
            return timestamp

        sorted_events = sorted(events, key=get_naive_timestamp)

        # Create table
        table = Table(title="Event Timeline", show_header=True)
        table.add_column("Time", style="cyan", no_wrap=True)
        table.add_column("Source", style="green")
        table.add_column("Type", style="yellow")
        table.add_column("Content", style="white")

        # Add events to table
        for event in sorted_events:
            time_str = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")

            # Format content
            if show_content:
                content = event.content
            else:
                content = event.content.replace("\n", " ")

            # Add metadata hints
            if event.metadata.get("type") == "user":
                content = f"👤 {content}"
            elif event.metadata.get("type") == "assistant":
                content = f"🤖 {content}"

            table.add_row(time_str, event.source, event.type.value, content)

        self.console.print(table)

    def show_summary_timeline(self, summaries: list[dict]) -> None:
        """
        Display summarized timeframes as a timeline.

        Args:
            summaries: List of timeframe summaries
        """
        if not summaries:
            self.console.print("[yellow]No summaries to display[/yellow]")
            return

        # Display summaries without table for better formatting
        self.console.print("\n[bold]Summary Timeline[/bold]\n")

        for summary in summaries:
            start = summary["start"].strftime("%Y-%m-%d %H:%M")
            end = summary["end"].strftime("%H:%M")

            # Print timeframe header
            self.console.print(
                f"[cyan]📅 {start} - {end}[/cyan] ([green]{summary['event_count']} events[/green])"
            )

            # Print summary with proper formatting
            summary_text = summary["summary"]
            # Remove any markdown backticks that might appear
            summary_text = summary_text.replace("```", "").strip()

            # Print summary with indentation
            for line in summary_text.split("\n"):
                if line.strip():
                    self.console.print(f"  {line}")

            self.console.print()  # Add blank line between summaries

    def show_stats(self, events: list[Event]) -> None:
        """Show statistics about events."""
        if not events:
            self.console.print("[yellow]No events to analyze[/yellow]")
            return

        # Calculate stats
        sources = {}
        types = {}

        for event in events:
            sources[event.source] = sources.get(event.source, 0) + 1
            types[event.type.value] = types.get(event.type.value, 0) + 1

        # Time range (make all timezone-naive for comparison)
        def get_naive_timestamp(event):
            timestamp = event.timestamp
            if timestamp.tzinfo is not None:
                return timestamp.replace(tzinfo=None)
            return timestamp

        sorted_events = sorted(events, key=get_naive_timestamp)
        time_range = sorted_events[-1].timestamp - sorted_events[0].timestamp

        # Display stats
        self.console.print("\n[bold]Event Statistics[/bold]")
        self.console.print(f"Total events: {len(events)}")
        self.console.print(f"Time range: {time_range}")

        self.console.print("\n[bold]By Source:[/bold]")
        for source, count in sources.items():
            self.console.print(f"  {source}: {count}")

        self.console.print("\n[bold]By Type:[/bold]")
        for event_type, count in types.items():
            self.console.print(f"  {event_type}: {count}")
