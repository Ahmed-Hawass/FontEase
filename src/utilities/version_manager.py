"""
Version management and update checking for Windows Font Customizer.
"""

import os
import json
import threading
import tkinter as tk
from tkinter import messagebox
from urllib.request import Request, urlopen
from urllib.error import URLError
import webbrowser
from typing import Optional, Dict, Tuple, Callable, Union, List, Any

from src.models.constants import VERSION, APP_NAME
from src.utilities.logger import AppLogger

# GitHub repository information - replace with your actual repository
REPO_OWNER = "Ahmed-Hawass"
REPO_NAME = "FontEase"
RELEASES_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
HOMEPAGE_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases/latest"

class VersionManager:
    """Manages version checking and updates for the application."""
    
    def _get_logger(self):
        if not hasattr(self, '_logger'):
            self._logger = AppLogger()
        return self._logger

    def __init__(self, app_version: str = VERSION) -> None:
        """Initialize the version manager.
        
        Args:
            app_version: Current application version
        """
        self.app_version: str = app_version
        self.latest_version: Optional[str] = None
        self.release_notes: Optional[str] = None
        self.update_available: bool = False
        self._check_thread: Optional[threading.Thread] = None
        self.last_error: Optional[str] = None
    
    def check_for_updates(self, auto_check: bool = False, callback: Optional[Callable[[bool], None]] = None) -> None:
        """Check for updates in a background thread.
        
        Args:
            auto_check: Whether this is an automatic check (suppresses messages on no updates)
            callback: Function to call when check is complete
        """
        self.last_error = None  # Reset last error before starting
        if self._check_thread and self._check_thread.is_alive():
            # Already checking
            return
            
        # Start check in background thread
        self._check_thread = threading.Thread(
            target=self._do_check_for_updates,
            args=(auto_check, callback),
            daemon=True
        )
        self._check_thread.start()
    
    def _do_check_for_updates(self, auto_check: bool = False, callback: Optional[Callable[[bool], None]] = None) -> None:
        """Perform the actual update check.
        
        Args:
            auto_check: Whether this is an automatic check
            callback: Function to call when check is complete
        """
        try:
            # Create a request with a user agent to avoid GitHub API limitations
            headers = {
                'User-Agent': f'{APP_NAME}/{VERSION}'
            }
            req = Request(RELEASES_URL, headers=headers)
            
            # Get latest release info
            with urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                self._get_logger().info("Fetched latest release info from GitHub", extra_context={"operation": "check_for_updates", "status": "success", "latest_version": data.get('tag_name', '0.0.0')})
            
            # Extract version number (remove 'v' prefix if present)
            latest_version = data.get('tag_name', '0.0.0')
            if latest_version.startswith('v'):
                latest_version = latest_version[1:]
                
            self.latest_version = latest_version
            self.release_notes = data.get('body', 'No release notes available.')
            
            # Compare versions
            update_available = self._is_newer_version(self.latest_version or "0.0.0")
            self.update_available = update_available
            if update_available:
                self._get_logger().info("Update available", extra_context={"operation": "check_for_updates", "update_available": True, "latest_version": self.latest_version})
            else:
                self._get_logger().info("No updates available", extra_context={"operation": "check_for_updates", "update_available": False, "latest_version": self.latest_version})
        except URLError as e:
            self.last_error = f"Network error: {str(e)}"
            self._get_logger().error(f"Failed to check for updates (network error): {str(e)}", exc_info=True, extra_context={"operation": "check_for_updates", "error_type": "URLError"})
        except Exception as e:
            self.last_error = str(e)
            self._get_logger().error(f"Failed to check for updates: {str(e)}", exc_info=True, extra_context={"operation": "check_for_updates"})
        
        # Call the callback if provided
        if callback:
            try:
                callback(self.update_available)
            except Exception as e:
                self._get_logger().error(f"Callback error in check_for_updates: {str(e)}", exc_info=True, extra_context={"operation": "check_for_updates", "callback": True})
    
    def _is_newer_version(self, version_str: str) -> bool:
        """Compare version strings to determine if an update is available.
        
        Args:
            version_str: Version string to compare against current version
            
        Returns:
            bool: True if version_str is newer than current version
        """
        try:
            # Parse version strings into tuples of integers
            current_parts = [int(x) for x in self.app_version.split('.')]
            new_parts = [int(x) for x in version_str.split('.')]
            
            # Pad with zeros if necessary
            while len(current_parts) < 3:
                current_parts.append(0)
            while len(new_parts) < 3:
                new_parts.append(0)
                
            # Compare version components
            for i in range(max(len(current_parts), len(new_parts))):
                current = current_parts[i] if i < len(current_parts) else 0
                new = new_parts[i] if i < len(new_parts) else 0
                
                if new > current:
                    return True
                elif new < current:
                    return False
                    
            # If we get here, versions are equal
            return False
        except ValueError:
            # If version format is invalid, assume no update
            print(f"Invalid version format: {version_str}")
            return False
    
    def _show_update_message(self) -> None:
        """Show a message about available updates."""
        result = messagebox.askyesno(
            "Update Available",
            f"A new version of {APP_NAME} is available!\n\n"
            f"Current version: {self.app_version}\n"
            f"Latest version: {self.latest_version}\n\n"
            f"Would you like to view the release page?"
        )
        
        if result:
            # Open web browser to release page
            webbrowser.open(HOMEPAGE_URL)
    
    def get_version_info(self) -> Dict[str, str]:
        """Get information about current and latest versions.
        
        Returns:
            dict: Dictionary with version information
        """
        return {
            'current_version': self.app_version,
            'latest_version': self.latest_version or 'Unknown',
            'update_available': 'Yes' if self.update_available else 'No',
            'release_notes': self.release_notes or 'No release notes available.',
            'last_error': self.last_error or 'No error'
        }

# Create a global instance of the version manager
version_manager = VersionManager() 