"""
Helper functions for the Windows Font Customizer application.
"""

import os
import sys
import ctypes
from win32comext.shell import shellcon
from win32comext.shell.shell import ShellExecuteEx
import win32con
import win32event
import win32process
import tkinter as tk
from tkinter import messagebox
from typing import Optional, Tuple

def get_resource_path(relative_path: str) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller
    
    Args:
        relative_path: Path relative to the application base directory
        
    Returns:
        str: Absolute path to the resource
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = getattr(sys, '_MEIPASS', None)
        if base_path is None:
            base_path = os.path.abspath(".")
            
        # Make sure the path exists before returning it
        full_path = os.path.join(base_path, relative_path)
        
        # Log the path for debugging
        print(f"Resource path: {full_path}")
        
        # If the resource isn't found at the expected path, search in common locations
        if not os.path.exists(full_path):
            # Try the current directory first
            alt_path = os.path.join(os.path.abspath("."), relative_path)
            if os.path.exists(alt_path):
                return alt_path
                
            # Try the parent directory
            alt_path = os.path.join(os.path.abspath(".."), relative_path)
            if os.path.exists(alt_path):
                return alt_path
                
            print(f"Warning: Resource not found: {full_path}")
            
        return full_path
    except Exception as e:
        print(f"Error finding resource: {e}")
        return os.path.join(os.path.abspath("."), relative_path)


# This section can include methods or utilities to dynamically update

class ToolTip:
    """Tooltip class for adding tooltips to widgets"""

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
        self.widget.bind("<Motion>", self.update_tooltip_position)

    def show_tooltip(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25

        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")

        # Static colors for tooltip
        bg_color = "#ffffff"
        fg_color = "#000000"
        border_color = "#000000"

        frame = tk.Frame(self.tooltip, bg=border_color)
        frame.pack(fill="both", expand=True)

        label = tk.Label(
            frame,
            text=self.text,
            bg=bg_color,
            fg=fg_color,
            wraplength=250,
            justify=tk.LEFT,
            padx=3,
            pady=3
        )
        label.pack(padx=1, pady=1)

    def hide_tooltip(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

    def update_tooltip_position(self, event):
        if self.tooltip:
            x = event.x_root + 25
            y = event.y_root + 25
            self.tooltip.wm_geometry(f"+{x}+{y}")