"""
FontEase - Main entry point

This module serves as the entry point for the FontEase application.
It handles application initialization and launches the main window.
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox
import pathlib

# Add the src directory to PYTHONPATH dynamically
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ui.main_window import MainWindow
from src.utilities.logger import AppLogger

# Set up AppData logs directory for logger
appdata = os.getenv('APPDATA')
if not appdata:
    raise EnvironmentError("APPDATA environment variable is not set.")
appdata_dir = os.path.join(appdata, 'FontEase')
logs_dir = os.path.join(appdata_dir, 'logs')
pathlib.Path(logs_dir).mkdir(parents=True, exist_ok=True)
log_file_path = os.path.join(logs_dir, 'FontEase.log')
logger = AppLogger(log_file=log_file_path)
logger.info("Application logger initialized", extra_context={"startup": True, "entry": "main.py"})

def main() -> None:
    """Main entry point of the application."""
    try:
        # Create the application window
        root = tk.Tk()
        app = MainWindow(root)
        
        # Start the application
        root.mainloop()
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True, extra_context={"entry": "main.py"})
        messagebox.showerror(
            "Error Starting Application",
            f"An error occurred while starting the application:\n\n{str(e)}"
        )
        sys.exit(1)

if __name__ == "__main__":
    main()