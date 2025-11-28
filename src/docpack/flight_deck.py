"""Flight Deck - A stunning TUI for testing the DocPack pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import (
    Button,
    DataTable,
    DirectoryTree,
    Footer,
    Header,
    Input,
    Label,
    Log,
    ProgressBar,
    Rule,
    Static,
)

from docpack.chunkers import ParagraphChunker
from docpack.embedders import SentenceTransformerEmbedder
from docpack.ingesters import get_ingester
from docpack.models import Document
from docpack.storage import DocPackStore


@dataclass
class PipelineStats:
    """Statistics tracked during pipeline execution."""

    files_discovered: int = 0
    files_processed: int = 0
    text_files: int = 0
    binary_files: int = 0
    chunks_created: int = 0
    embeddings_generated: int = 0
    total_bytes: int = 0
    current_file: str = ""
    status: str = "idle"
    start_time: datetime | None = None
    end_time: datetime | None = None

    @property
    def elapsed(self) -> str:
        if not self.start_time:
            return "00:00"
        end = self.end_time or datetime.now()
        delta = end - self.start_time
        minutes, seconds = divmod(int(delta.total_seconds()), 60)
        return f"{minutes:02d}:{seconds:02d}"

    @property
    def rate(self) -> str:
        if not self.start_time or self.files_processed == 0:
            return "-- files/s"
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if elapsed == 0:
            return "-- files/s"
        return f"{self.files_processed / elapsed:.1f} files/s"

    def copy(self) -> "PipelineStats":
        """Create a copy of the stats."""
        return PipelineStats(
            files_discovered=self.files_discovered,
            files_processed=self.files_processed,
            text_files=self.text_files,
            binary_files=self.binary_files,
            chunks_created=self.chunks_created,
            embeddings_generated=self.embeddings_generated,
            total_bytes=self.total_bytes,
            current_file=self.current_file,
            status=self.status,
            start_time=self.start_time,
            end_time=self.end_time,
        )


class StatsPanel(Static):
    """Real-time statistics display."""

    def compose(self) -> ComposeResult:
        yield Static(id="stats-content")

    def on_mount(self) -> None:
        self.update_display(PipelineStats())

    def update_display(self, stats: PipelineStats) -> None:
        content = self.query_one("#stats-content", Static)
        status_color = {
            "idle": "dim",
            "loading": "yellow",
            "running": "green",
            "complete": "cyan",
            "error": "red",
        }.get(stats.status, "white")

        content.update(f"""[b]STATUS[/b]  [{status_color}]{stats.status.upper()}[/]

[b]TIME[/b]    {stats.elapsed}  {stats.rate}

[b]FILES[/b]
  Discovered  [cyan]{stats.files_discovered:,}[/]
  Processed   [green]{stats.files_processed:,}[/]
  Text        [blue]{stats.text_files:,}[/]
  Binary      [dim]{stats.binary_files:,}[/]

[b]SEMANTIC[/b]
  Chunks      [magenta]{stats.chunks_created:,}[/]
  Embeddings  [yellow]{stats.embeddings_generated:,}[/]

[b]SIZE[/b]
  Total       [cyan]{stats.total_bytes / 1024:.1f} KB[/]""")


class CurrentFileDisplay(Static):
    """Display for the currently processing file."""

    def compose(self) -> ComposeResult:
        yield Static("[dim]Waiting for source...[/]", id="current-file-content")

    def update_file(self, file: str) -> None:
        content = self.query_one("#current-file-content", Static)
        if file:
            display = file if len(file) < 50 else "..." + file[-47:]
            content.update(f"[bold cyan]>[/] {display}")
        else:
            content.update("[dim]Waiting for source...[/]")


class FileLogTable(DataTable):
    """Live file processing log as a table."""

    def on_mount(self) -> None:
        self.add_columns("File", "Type", "Chunks", "Size")
        self.cursor_type = "row"

    def add_file(self, path: str, is_binary: bool, chunks: int, size: int) -> None:
        file_type = "[dim]binary[/]" if is_binary else "[blue]text[/]"
        chunk_str = "[dim]--[/]" if is_binary else f"[magenta]{chunks}[/]"
        size_str = f"{size / 1024:.1f}KB" if size >= 1024 else f"{size}B"
        display_name = Path(path).name
        if len(display_name) > 30:
            display_name = display_name[:27] + "..."
        self.add_row(display_name, file_type, chunk_str, size_str)
        self.scroll_end()


class FlightDeck(App):
    """The DocPack Flight Deck - Pipeline Testing TUI."""

    # Messages for thread-safe communication
    class StatsUpdated(Message):
        def __init__(self, stats: PipelineStats) -> None:
            self.stats = stats
            super().__init__()

    class LogMessage(Message):
        def __init__(self, message: str) -> None:
            self.message = message
            super().__init__()

    class FileProcessed(Message):
        def __init__(self, path: str, is_binary: bool, chunks: int, size: int) -> None:
            self.path = path
            self.is_binary = is_binary
            self.chunks = chunks
            self.size = size
            super().__init__()

    CSS = """
    Screen {
        background: $surface;
    }

    Header {
        background: $primary-darken-3;
        color: $text;
    }

    Footer {
        background: $primary-darken-3;
    }

    #main-container {
        layout: horizontal;
        height: 100%;
    }

    #left-panel {
        width: 35;
        background: $surface-darken-1;
        border-right: solid $primary-darken-2;
        padding: 1;
    }

    #center-panel {
        width: 1fr;
        padding: 1;
    }

    #right-panel {
        width: 30;
        background: $surface-darken-1;
        border-left: solid $primary-darken-2;
        padding: 1;
    }

    StatsPanel {
        height: auto;
        padding: 1;
        background: $surface-darken-2;
        border: round $primary;
        margin-bottom: 1;
    }

    CurrentFileDisplay {
        height: 3;
        padding: 1;
        background: $boost;
        border: round $secondary;
        margin-bottom: 1;
    }

    #source-input-container {
        height: auto;
        margin-bottom: 1;
    }

    #source-input {
        margin-bottom: 1;
    }

    #action-buttons {
        layout: horizontal;
        height: 3;
        margin-bottom: 1;
    }

    #action-buttons Button {
        margin-right: 1;
    }

    #freeze-btn {
        background: $success;
    }

    #freeze-btn:hover {
        background: $success-darken-1;
    }

    #clear-btn {
        background: $warning;
    }

    FileLogTable {
        height: 100%;
        border: round $primary-darken-1;
    }

    #progress-container {
        height: 3;
        margin-bottom: 1;
    }

    #progress-bar {
        width: 100%;
    }

    #log-panel {
        height: 12;
        border: round $primary-darken-2;
        background: $surface-darken-2;
    }

    .section-title {
        text-style: bold;
        color: $text;
        margin-bottom: 1;
    }

    DirectoryTree {
        height: 100%;
        border: round $primary-darken-1;
        background: $surface-darken-2;
    }

    #output-info {
        height: auto;
        padding: 1;
        background: $surface-darken-2;
        border: round $accent;
    }
    """

    BINDINGS = [
        Binding("f", "freeze", "Freeze", show=True),
        Binding("c", "clear", "Clear", show=True),
        Binding("q", "quit", "Quit", show=True),
        Binding("d", "toggle_dark", "Toggle Dark Mode"),
    ]

    TITLE = "DocPack Flight Deck"
    SUB_TITLE = "Pipeline Testing Console"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="main-container"):
            # Left panel - Stats & Controls
            with Vertical(id="left-panel"):
                yield Label("MISSION CONTROL", classes="section-title")
                yield StatsPanel()
                yield CurrentFileDisplay()
                yield Rule()
                with Container(id="source-input-container"):
                    yield Label("Source Path")
                    yield Input(
                        placeholder="Enter folder or .zip path...",
                        id="source-input",
                    )
                with Horizontal(id="action-buttons"):
                    yield Button("FREEZE", id="freeze-btn", variant="success")
                    yield Button("Clear", id="clear-btn", variant="warning")
                yield Rule()
                with Container(id="output-info"):
                    yield Static(
                        "[b]Output[/]\n[dim]output.docpack[/]",
                        id="output-label",
                    )

            # Center panel - File processing log
            with Vertical(id="center-panel"):
                yield Label("PROCESSING LOG", classes="section-title")
                with Container(id="progress-container"):
                    yield ProgressBar(id="progress-bar", show_eta=False)
                yield FileLogTable(id="file-log")
                yield Rule()
                yield Label("SYSTEM LOG", classes="section-title")
                yield Log(id="log-panel", highlight=True, auto_scroll=True)

            # Right panel - Directory browser
            with Vertical(id="right-panel"):
                yield Label("FILE BROWSER", classes="section-title")
                yield DirectoryTree(Path.cwd(), id="dir-tree")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the app on mount."""
        self._log("Flight Deck initialized")
        self._log("Enter a source path and press FREEZE to begin")

    def _log(self, message: str) -> None:
        """Add a message to the system log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.query_one("#log-panel", Log).write_line(f"[{timestamp}] {message}")

    # Message handlers for thread-safe updates
    def on_flight_deck_stats_updated(self, event: StatsUpdated) -> None:
        """Handle stats update from worker thread."""
        stats = event.stats
        self.query_one(StatsPanel).update_display(stats)
        self.query_one(CurrentFileDisplay).update_file(stats.current_file)
        if stats.files_discovered > 0:
            progress = stats.files_processed / stats.files_discovered
            self.query_one("#progress-bar", ProgressBar).update(progress=progress)

    def on_flight_deck_log_message(self, event: LogMessage) -> None:
        """Handle log message from worker thread."""
        self._log(event.message)

    def on_flight_deck_file_processed(self, event: FileProcessed) -> None:
        """Handle file processed from worker thread."""
        self.query_one("#file-log", FileLogTable).add_file(
            event.path, event.is_binary, event.chunks, event.size
        )

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        """Handle file selection from directory tree."""
        self.query_one("#source-input", Input).value = str(event.path)

    def on_directory_tree_directory_selected(
        self, event: DirectoryTree.DirectorySelected
    ) -> None:
        """Handle directory selection from directory tree."""
        self.query_one("#source-input", Input).value = str(event.path)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "freeze-btn":
            self.action_freeze()
        elif event.button.id == "clear-btn":
            self.action_clear()

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.dark = not self.dark

    def action_clear(self) -> None:
        """Clear the log and reset stats."""
        self.query_one(StatsPanel).update_display(PipelineStats())
        self.query_one(CurrentFileDisplay).update_file("")
        self.query_one("#file-log", FileLogTable).clear()
        self.query_one("#log-panel", Log).clear()
        self.query_one("#progress-bar", ProgressBar).update(progress=0)
        self._log("Cleared - ready for new run")

    def action_freeze(self) -> None:
        """Start the freeze pipeline."""
        source = self.query_one("#source-input", Input).value.strip()
        if not source:
            self._log("[red]ERROR: No source path specified[/]")
            return
        self.run_freeze(source)

    @work(exclusive=True, thread=True)
    def run_freeze(self, source: str) -> None:
        """Run the freeze pipeline in a background thread."""
        source_path = Path(source)
        output_path = Path("output.docpack")

        # Reset stats
        stats = PipelineStats()
        stats.status = "loading"
        stats.start_time = datetime.now()
        self.post_message(self.StatsUpdated(stats.copy()))
        self.post_message(self.LogMessage(f"Loading source: {source}"))

        # Validate source
        if not source_path.exists():
            stats.status = "error"
            self.post_message(self.StatsUpdated(stats.copy()))
            self.post_message(self.LogMessage(f"[red]ERROR: Path not found: {source}[/]"))
            return

        # Get ingester
        ingester = get_ingester(source_path)
        if ingester is None:
            stats.status = "error"
            self.post_message(self.StatsUpdated(stats.copy()))
            self.post_message(
                self.LogMessage("[red]ERROR: Unsupported source type (use folder or .zip)[/]")
            )
            return

        self.post_message(self.LogMessage(f"Ingester: {ingester.source_type}"))

        # Initialize components
        self.post_message(self.LogMessage("Loading embedding model..."))
        try:
            embedder = SentenceTransformerEmbedder()
            chunker = ParagraphChunker()
        except Exception as e:
            stats.status = "error"
            self.post_message(self.StatsUpdated(stats.copy()))
            self.post_message(
                self.LogMessage(f"[red]ERROR: Failed to load embedder: {e}[/]")
            )
            return

        self.post_message(
            self.LogMessage(f"Model: {embedder.model_name} ({embedder.dimension}D)")
        )

        # Initialize store
        store = DocPackStore(output_path)
        store.initialize()
        store.set_metadata("source", str(source_path.absolute()))
        store.set_metadata("source_type", ingester.source_type)
        store.set_metadata("created_at", datetime.now().isoformat())
        store.set_metadata("embedding_model", embedder.model_name)

        stats.status = "running"
        self.post_message(self.StatsUpdated(stats.copy()))
        self.post_message(self.LogMessage("[green]Pipeline running...[/]"))

        # First pass - count files
        self.post_message(self.LogMessage("Scanning source..."))
        docs_list: list[Document] = []
        for doc in ingester.ingest(source_path):
            docs_list.append(doc)
            stats.files_discovered += 1
            if stats.files_discovered % 50 == 0:
                self.post_message(self.StatsUpdated(stats.copy()))

        self.post_message(self.StatsUpdated(stats.copy()))
        self.post_message(self.LogMessage(f"Found {stats.files_discovered} files"))

        # Process files
        for doc in docs_list:
            stats.current_file = doc.metadata.path
            stats.total_bytes += doc.metadata.size_bytes

            store.store_document(doc)
            chunks_count = 0

            if doc.content:
                chunks = chunker.chunk(doc.content, doc.metadata.path)
                if chunks:
                    chunk_ids = store.store_chunks(chunks)
                    texts = [c.text for c in chunks]
                    embeddings = embedder.embed(texts)
                    store.store_embeddings(chunk_ids, embeddings)
                    chunks_count = len(chunks)
                    stats.chunks_created += chunks_count
                    stats.embeddings_generated += chunks_count
                stats.text_files += 1
            else:
                stats.binary_files += 1

            stats.files_processed += 1
            self.post_message(self.StatsUpdated(stats.copy()))
            self.post_message(
                self.FileProcessed(
                    doc.metadata.path,
                    doc.metadata.is_binary,
                    chunks_count,
                    doc.metadata.size_bytes,
                )
            )

        # Complete
        stats.status = "complete"
        stats.current_file = ""
        stats.end_time = datetime.now()
        self.post_message(self.StatsUpdated(stats.copy()))
        self.post_message(
            self.LogMessage(
                f"[cyan]COMPLETE: {stats.files_processed} files, "
                f"{stats.chunks_created} chunks -> {output_path}[/]"
            )
        )


def main() -> None:
    """Run the Flight Deck TUI."""
    app = FlightDeck()
    app.run()


if __name__ == "__main__":
    main()
