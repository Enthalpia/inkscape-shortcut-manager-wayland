import subprocess
from typing import Callable, Optional
import queue
import os

from parser_base import ParserBase
import global_var
from utils import HyprlandPlugin

class TextModeParser(ParserBase):
    """Open a small nvim floating window for inputting text in inkscape."""

    def __init__(
        self,
        log_queue: queue.Queue,
        title: str = "NVIM-POPUP",
        file_to_edit: Optional[str] = None,
        callback: Optional[Callable[[], None]] = None,
    ):
        # Initialize base class with a proper name
        super().__init__(log_queue, name="TextModeParser")
        self.title = title
        self.file_to_edit = file_to_edit
        self.callback = callback

    def start(self):
        """Start the parser thread."""
        self._start_thread(self._launch_nvim)

    def stop(self):
        """Stop the parser thread (called externally if needed)."""
        self._stop_thread()

    def _launch_nvim(self) -> None:
        """Launch a terminal running Neovim, wait for exit, then call callback."""
        # Build terminal command
        terminal_cmd = [
            "kitty",
            "--class", "kitty-float",
            "--title", self.title,
        ]

        # Handle file argument: create empty file only if it does not exist (no truncation)
        if self.file_to_edit:
            # Create file if missing, but never truncate existing content
            if not os.path.exists(self.file_to_edit):
                # Use 'x' to avoid race, but 'a' is fine for simple creation
                open(self.file_to_edit, "a").close()
            terminal_cmd.extend(["nvim", str(self.file_to_edit)])
        else:
            terminal_cmd.append("nvim")

        self.log_queue.put(f"Launching terminal with command: {' '.join(terminal_cmd)}")

        # Launch Kitty and wait for it to finish
        global_var.IS_INKSCAPE_ACTIVE = False
        HyprlandPlugin.toggle_config_file()  # Ensure config is set for text mode
        proc = subprocess.Popen(terminal_cmd)
        proc.wait()

        # After Neovim exits, invoke callback (if any)
        # Do NOT call self.stop() here – the thread will exit naturally
        if self.callback and callable(self.callback):
            self.callback()