"""
Main window for the Windows Font Customizer application.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import json

from src.models.constants import APP_NAME, VERSION, AUTHOR, YEAR, PREVIEW_TEXT, PADDING
from src.utilities.helpers import ToolTip, get_resource_path
from src.core.font_manager import (
    get_installed_fonts, 
    detect_current_system_font, 
    apply_system_font, 
    reset_system_font,
    install_font,
    open_windows_fonts_folder
)
from src.utilities.logger import AppLogger

class MainWindow:
    """Main window for the Windows Font Customizer application."""
    
    def __init__(self, root):
        """Initialize the main window.
        
        Args:
            root: The root tkinter window
        """
        self.root = root
        self.root.title(f"{APP_NAME} v{VERSION}")
        
        # Set up logger
        self.logger = AppLogger()
        self.logger.info("Application started", extra_context={"startup": True})
        
        # Set window icon from assets if available
        try:
            icon_path = get_resource_path(os.path.join("assets", "icon.ico"))
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
            else:
                self.logger.info("Icon not found, continuing without it", extra_context={"icon_path": icon_path})
        except Exception as e:
            self.logger.warning(f"Could not set window icon: {e}", extra_context={"icon_path": icon_path})
        
        # Set up application directories
        self.setup_app_directories()
        
        # Set up application files
        self.setup_app_files()

        # Config file path
        self.config_path = self.files['config_file']
        
        # FontEase temp directory
        self.fontease_temp_dir = self.dirs['temp']

        # Load config
        self.config = self.load_config()
        all_fonts = get_installed_fonts()
        self.config = self.validate_config(self.config, all_fonts)

        # Set up preview size and last font selection from config
        self.preview_size_var = tk.IntVar()
        self.font_var = tk.StringVar()
        self.preview_size_var.set(self.config.get('preview_size', 20))
        self.font_var.set(self.config.get('last_selected_font', ''))

        # Initialize status variable
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        
        # Set up UI
        self.setup_ui()
        
        # Load installed fonts
        self.load_installed_fonts()
        
        # Center the window on screen
        self.center_window()
        
        # Set up window resize event
        self.root.bind("<Configure>", self.on_window_resize)
        
        # Set up window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.close_application)
        
        # Check for updates in the background after startup (3 second delay)
        self.root.after(3000, self.silent_update_check)
    
    def setup_app_directories(self):
        """Set up application directories for resources and data."""
        appdata = os.getenv('APPDATA')
        if not appdata:
            raise EnvironmentError("APPDATA environment variable is not set.")
        self.app_data_dir = os.path.join(appdata, 'FontEase')

        # Create subdirectories
        self.dirs = {
            'logs': os.path.join(self.app_data_dir, 'logs'),
            'temp': os.path.join(self.app_data_dir, 'temp'),
            'config': os.path.join(self.app_data_dir, 'config')
        }

        # Centralized directory creation
        for directory_name, directory_path in self.dirs.items():
            self._create_directory(directory_name, directory_path)

    def setup_app_files(self):
        """Set up application files and ensure they are ready for use."""
        # Define required files with improved names
        self.files = {
            'log_file': os.path.join(self.dirs['logs'], 'FontEase.log'),
            'config_file': os.path.join(self.dirs['config'], 'FontEase_settings.json')
        }

        # Ensure each file exists
        for file_name, file_path in self.files.items():
            self._create_file(file_name, file_path)

    def _create_file(self, name, path):
        """Helper function to create a file if it doesn't exist."""
        if not os.path.exists(path):
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write('')  # Create an empty file
                self.logger.info(f"Created {name}: {path}", extra_context={"file": path})
            except Exception as e:
                self.logger.error(f"Failed to create {name} {path}: {str(e)}", exc_info=True, extra_context={"file": path})

    def _create_directory(self, name, path):
        """Helper function to create a directory if it doesn't exist."""
        if not os.path.exists(path):
            try:
                os.makedirs(path)
                self.logger.info(f"Created {name} directory: {path}", extra_context={"directory": path})
            except Exception as e:
                self.logger.error(f"Failed to create {name} directory {path}: {str(e)}", exc_info=True, extra_context={"directory": path})
    
    def _cleanup_resources(self):
        """Clean up temporary files and resources."""
        import time
        
        try:
            # Clean temp directory
            temp_dir = self.dirs['temp']
            current_time = time.time()
            
            for filename in os.listdir(temp_dir):
                filepath = os.path.join(temp_dir, filename)
                try:
                    if current_time - os.path.getctime(filepath) > 86400:  # 24 hours
                        os.remove(filepath)
                except Exception as e:
                    self.logger.warning(f"Could not remove temp file {filepath}: {e}", extra_context={"file": filepath})
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}", exc_info=True)
    
    def setup_ui(self):
        """Set up the main user interface components."""
        # Create main frame with padding
        main_frame = ttk.Frame(self.root, padding=PADDING["large"])
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create menu bar
        self.create_menu_bar()
     
        # Font selection section
        font_frame = ttk.LabelFrame(main_frame, text="Font Selection", padding=PADDING["medium"])
        font_frame.pack(fill=tk.X, pady=(PADDING["medium"], PADDING["large"]))
        
        # Font dropdown
        font_label = ttk.Label(font_frame, text="Select Font:")
        font_label.grid(row=0, column=0, sticky=tk.W, padx=(0, PADDING["small"]), pady=PADDING["small"])
        
        self.font_dropdown = ttk.Combobox(font_frame, textvariable=self.font_var, width=30, state="readonly")
        self.font_dropdown.grid(row=0, column=1, sticky=tk.W, pady=PADDING["small"])
        self.font_dropdown.bind("<<ComboboxSelected>>", self.preview_font)
        
        # Add tooltip to font dropdown
        ToolTip(self.font_dropdown, "Select a font to preview and apply")
        
        # Current font display
        current_font_label = ttk.Label(font_frame, text="Current System Font:")
        current_font_label.grid(row=1, column=0, sticky=tk.W, padx=(0, PADDING["small"]), pady=PADDING["small"])
        
        self.current_font_var = tk.StringVar(value="Detecting...")
        current_font_display = ttk.Label(font_frame, textvariable=self.current_font_var, foreground="blue", font=("Segoe UI", 12))
        current_font_display.grid(row=1, column=1, sticky=tk.W, pady=PADDING["small"])
        
        # Font size selector for preview
        size_label = ttk.Label(font_frame, text="Preview Size:")
        size_label.grid(row=2, column=0, sticky=tk.W, padx=(0, PADDING["small"]), pady=PADDING["small"])
        
        size_frame = ttk.Frame(font_frame)
        size_frame.grid(row=2, column=1, sticky=tk.W, pady=PADDING["small"])
        
        size_decrease = ttk.Button(size_frame, text="-", width=3, command=self.decrease_preview_font_size)
        size_decrease.pack(side=tk.LEFT, padx=(0, PADDING["small"]))
        ToolTip(size_decrease, "Decrease preview font size (Ctrl+-)")
        
        size_label = ttk.Label(size_frame, textvariable=self.preview_size_var, width=3, anchor=tk.CENTER)
        size_label.pack(side=tk.LEFT, padx=PADDING["small"])
        
        size_increase = ttk.Button(size_frame, text="+", width=3, command=self.increase_preview_font_size)
        size_increase.pack(side=tk.LEFT, padx=PADDING["small"])
        ToolTip(size_increase, "Increase preview font size (Ctrl++)")
        
        # Simple preview frame
        preview_frame = ttk.LabelFrame(main_frame, text="Font Preview", padding=PADDING["medium"])
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, PADDING["large"]))
        preview_frame.pack_propagate(False)  # Prevent resizing to fit children
        preview_frame.config(width=600, height=220)  # Set fixed preview frame size
        
        # Preview text with scrollbar
        preview_container = ttk.Frame(preview_frame)
        preview_container.pack(fill=tk.BOTH, expand=True)
        preview_container.pack_propagate(False)
        preview_container.config(width=580, height=180)  # Set fixed container size
        
        preview_scrollbar = ttk.Scrollbar(preview_container)
        preview_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Preview text widget
        font_name = self.font_var.get() or "Segoe UI"
        font_size = self.preview_size_var.get()
        self.preview_text = tk.Text(preview_container, height=8, width=60, wrap=tk.WORD, 
                                  font=(font_name, font_size),
                                  yscrollcommand=preview_scrollbar.set,
                                  relief=tk.FLAT,
                                  borderwidth=1,
                                  padx=PADDING["medium"],
                                  pady=PADDING["medium"],
                                  selectbackground="lightblue",
                                  selectforeground="black")
        self.preview_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)  # Do not expand
        preview_scrollbar.config(command=self.preview_text.yview)
        
        # Set default preview text
        self.preview_text.insert(tk.END, PREVIEW_TEXT)
        self.preview_text.tag_add("preview", "1.0", tk.END)
        self.preview_text.tag_config("preview", font=(font_name, font_size))
        self.preview_text.config(state=tk.DISABLED)  # Make read-only
        
        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, PADDING["medium"]))
        
        # Refresh button to refresh font list
        refresh_button = ttk.Button(button_frame, text="Refresh Fonts", command=self.load_installed_fonts)
        refresh_button.pack(side=tk.LEFT, padx=(0, PADDING["small"]))
        ToolTip(refresh_button, "Refresh the list of installed fonts (F5)")
        
        # Install Font button
        install_button = ttk.Button(button_frame, text="Install Font", command=self.install_font_handler)
        install_button.pack(side=tk.LEFT, padx=(0, PADDING["small"]))
        ToolTip(install_button, "Install TTF/OTF font files to your system (Ctrl+I)")
        
        # Apply button
        apply_button = ttk.Button(button_frame, text="Apply Font", command=self.apply_font_handler)
        apply_button.pack(side=tk.RIGHT, padx=(0, PADDING["small"]))
        ToolTip(apply_button, "Apply the selected font as the system font (Ctrl+A)")
        
        # Reset button
        reset_button = ttk.Button(button_frame, text="Reset to Default", command=self.reset_font_handler)
        reset_button.pack(side=tk.RIGHT)
        ToolTip(reset_button, "Reset to the default Segoe UI font (Ctrl+R)")
        
        # Status bar
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, style="Status.TLabel")
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Set up keyboard shortcuts
        self.setup_keyboard_shortcuts()
        
        # Set initial focus to the font dropdown for keyboard navigation
        self.font_dropdown.focus_set()
        
        # Optionally, set a fixed window size for the main window
        self.root.minsize(650, 500)
        self.root.geometry("700x540")
    
    def create_menu_bar(self):
        """Create the application menu bar."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Install Font", command=self.install_font_handler, accelerator="Ctrl+I")
        file_menu.add_command(label="Exit", command=self.root.destroy, accelerator="Alt+F4")
        
        # Actions menu
        actions_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Actions", menu=actions_menu)
        actions_menu.add_command(label="Apply Font", command=self.apply_font_handler, accelerator="Ctrl+A")
        actions_menu.add_command(label="Reset to Default", command=self.reset_font_handler, accelerator="Ctrl+R")
        actions_menu.add_command(label="Refresh Font List", command=self.load_installed_fonts, accelerator="F5")
        actions_menu.add_command(label="Open Fonts Folder", command=open_windows_fonts_folder, accelerator="Ctrl+O")
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Check for Updates", command=self.check_for_updates)
        help_menu.add_command(label="View License", command=self.show_license)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self.show_about, accelerator="F1")
    
    def setup_keyboard_shortcuts(self):
        """Set up keyboard shortcuts for common actions."""
        # File menu shortcuts
        self.root.bind('<Control-i>', lambda event: self.install_font_handler())
        
        # Actions menu shortcuts
        self.root.bind('<Control-a>', lambda event: self.apply_font_handler())
        self.root.bind('<Control-r>', lambda event: self.reset_font_handler())
        self.root.bind('<F5>', lambda event: self.load_installed_fonts())
        self.root.bind('<Control-o>', lambda event: open_windows_fonts_folder())
        
        # View menu shortcuts
        self.root.bind('<Control-plus>', self.increase_preview_font_size)
        self.root.bind('<Control-equal>', self.increase_preview_font_size)  # For keyboards where + requires shift
        self.root.bind('<Control-minus>', self.decrease_preview_font_size)
        self.root.bind('<Control-0>', self.reset_preview_font_size)
        
        # Help menu shortcuts
        self.root.bind('<F1>', lambda event: self.show_about())
        
        # Tab navigation for accessibility
        self.root.bind('<Tab>', self.focus_next_widget)
        self.root.bind('<Shift-Tab>', self.focus_previous_widget)
        
        # Enter key to activate buttons when focused
        self.root.bind('<Return>', self.activate_focused_widget)
    
    def focus_next_widget(self, event):
        """Move focus to the next widget in the tab order."""
        event.widget.tk_focusNext().focus()
        return "break"  # Prevent default tab behavior
    
    def focus_previous_widget(self, event):
        """Move focus to the previous widget in the tab order."""
        event.widget.tk_focusPrev().focus()
        return "break"  # Prevent default tab behavior
    
    def activate_focused_widget(self, event):
        """Activate the currently focused widget (button, etc.)."""
        widget = event.widget
        if isinstance(widget, (tk.Button, ttk.Button)) and hasattr(widget, 'invoke'):
            widget.invoke()
        return "break"  # Prevent default behavior
    
    def load_installed_fonts(self):
        """Load all installed fonts from the system."""
        try:
            self.status_var.set("Loading fonts...")
            self.root.update_idletasks()
            
            # Get all installed fonts in Windows
            all_fonts = get_installed_fonts()
            self.font_dropdown['values'] = all_fonts
            
            # Show current system font in label
            current_font = detect_current_system_font()
            if current_font:
                self.current_font_var.set(current_font)
            else:
                self.current_font_var.set('Unknown')
            
            # Always try to select last selected font from config
            last_font = self.config.get('last_selected_font', '')
            if last_font and self.select_font_in_dropdown(last_font):
                pass
            elif current_font and self.select_font_in_dropdown(current_font):
                pass
            elif all_fonts:
                self.font_dropdown.current(0)
                self.preview_font(None)
            
            self.status_var.set(f"Ready - {len(all_fonts)} fonts loaded")
        except Exception as e:
            self.status_var.set("Error loading fonts")
            self.logger.error(f"Failed to load fonts: {str(e)}", exc_info=True)
            messagebox.showerror("Error", f"Failed to load fonts: {str(e)}")
    
    def select_font_in_dropdown(self, font_name):
        """Try to select the specified font in the dropdown."""
        try:
            values = self.font_dropdown['values']
            for i, f in enumerate(values):
                if f.lower() == font_name.lower():
                    self.font_dropdown.current(i)
                    self.preview_font(None)
                    # Save last selected font to config
                    self.config['last_selected_font'] = font_name
                    self.save_config()
                    return True
            return False
        except Exception as e:
            self.logger.error(f"Error selecting font in dropdown: {str(e)}", exc_info=True, extra_context={"font_name": font_name})
            return False
    
    def preview_font(self, event):
        """Update the preview with the selected font."""
        selected_font = self.font_var.get()
        if not selected_font:
            return
        
        try:
            # Update text preview
            self.preview_text.config(state=tk.NORMAL)
            for tag in self.preview_text.tag_names():
                if tag != "sel":
                    self.preview_text.tag_delete(tag)
            
            self.preview_text.tag_add("preview", "1.0", tk.END)
            self.preview_text.tag_config("preview", font=(selected_font, self.preview_size_var.get()))
            self.preview_text.config(state=tk.DISABLED)  # Make read-only
            
            self.status_var.set(f"Previewing: {selected_font}")
            # Save preview size and last selected font to config
            self.config['preview_size'] = self.preview_size_var.get()
            self.config['last_selected_font'] = selected_font
            self.save_config()
        except Exception as e:
            self.status_var.set(f"Error in preview: {str(e)}")
            self.logger.error(f"Error in preview: {str(e)}", exc_info=True, extra_context={"font": selected_font})
    
    def apply_font_handler(self):
        """Apply the selected font as the Windows system font."""
        # Get the selected font
        selected_font = self.font_var.get()
        
        if not selected_font:
            self.logger.warning("No font selected for application.")
            messagebox.showwarning("Warning", "Please select a font to apply.")
            return
        
        # Confirm with user
        result = messagebox.askokcancel(
            "Confirm Font Change",
            f"Are you sure you want to change the system font to {selected_font}?\n\n" +
            "This may affect the appearance of system dialogs and applications.\n\n" +
            "You can restore the default font at any time.")
        if not result:
            self.status_var.set("Font application canceled by user.")
            return
        
        # Apply the font
        try:
            self.root.config(cursor="wait")
            self.status_var.set(f"Applying font: {selected_font}...")
            self.root.update_idletasks()
            
            from src.core.font_manager import apply_system_font
            success = apply_system_font(selected_font, temp_dir=self.fontease_temp_dir)
            if success:
                messagebox.showinfo(
                    "Font Applied",
                    f"Font changed to {selected_font}.\n\n" +
                    "Please restart your computer for the changes to take full effect."
                )
                self.status_var.set(f"Font applied: {selected_font} (restart required)")
            else:
                raise Exception("Failed to apply font")
        except Exception as e:
            self.logger.error(f"Failed to apply font: {str(e)}", exc_info=True)
            messagebox.showerror("Error", f"Failed to apply font: {str(e)}")
            self.status_var.set("Error applying font")
        finally:
            # Restore cursor
            self.root.config(cursor="")
    
    def reset_font_handler(self):
        """Reset the system font to the default Segoe UI."""
        # Confirm with user
        result = messagebox.askokcancel(
            "Reset System Font",
            "Are you sure you want to reset the system font to the default (Segoe UI)?\n\n" +
            "This will restore the original Windows font settings.")
        if not result:
            self.status_var.set("Font reset canceled by user.")
            return
        
        # Reset the font
        try:
            self.root.config(cursor="wait")
            self.status_var.set("Resetting font to default...")
            self.root.update_idletasks()
            
            from src.core.font_manager import reset_system_font
            success = reset_system_font(temp_dir=self.fontease_temp_dir)
            if success:
                messagebox.showinfo(
                    "Font Reset",
                    "Font successfully reset to default (Segoe UI).\n\n" +
                    "Please restart your computer for the changes to take full effect."
                )
                self.status_var.set("Font reset to default (restart required)")
            else:
                raise Exception("Failed to reset font")
        except Exception as e:
            self.logger.error(f"Failed to reset font: {str(e)}", exc_info=True)
            messagebox.showerror("Error", f"Failed to reset font: {str(e)}")
            self.status_var.set("Error resetting font")
        finally:
            self.root.config(cursor="")
    
    def install_font_handler(self):
        """Handle font installation."""
        success_count, failed_fonts = install_font()
        
        # Show result message
        if success_count > 0:
            if failed_fonts:
                messagebox.showinfo("Font Installation", 
                                   f"Successfully installed {success_count} font(s).\n\n" +
                                   f"Failed to install {len(failed_fonts)} font(s):\n" +
                                   "\n".join(failed_fonts))
            else:
                messagebox.showinfo("Font Installation", f"Successfully installed {success_count} font(s).")
            
            # Refresh font list
            self.load_installed_fonts()
        elif failed_fonts:
            messagebox.showerror("Font Installation", 
                               "Failed to install any fonts.\n\n" +
                               "This operation requires administrator privileges.")
    
    def show_about(self):
        """Show the About dialog."""
        # Create About dialog
        about_window = tk.Toplevel(self.root)
        about_window.geometry("350x250")  # Adjusted size
        about_window.resizable(False, False)
        about_window.transient(self.root)  # Set as transient to main window
        about_window.grab_set()  # Make modal

        # Try to set icon
        try:
            icon_path = get_resource_path(os.path.join("assets", "icon.ico"))
            if os.path.exists(icon_path):
                about_window.iconbitmap(icon_path)
        except Exception as e:
            self.logger.error(f"Error setting icon: {str(e)}")

        # Main frame with padding
        main_frame = ttk.Frame(about_window, padding=PADDING["large"])
        main_frame.pack(fill=tk.BOTH, expand=True)

        # App name and version
        app_name_label = ttk.Label(main_frame, text=f"{APP_NAME} v{VERSION}", font=("Segoe UI", 14, "bold"))
        app_name_label.pack(pady=(0, PADDING["medium"]))

        # Description
        desc_text = "Change your Windows font with ease."
        desc_label = ttk.Label(main_frame, text=desc_text, justify=tk.CENTER, wraplength=300)
        desc_label.pack(pady=(0, PADDING["medium"]))

        # Copyright info
        copyright_label = ttk.Label(main_frame, text=f"  {YEAR} {AUTHOR}", font=("Segoe UI", 10))
        copyright_label.pack(pady=(0, PADDING["small"]))

        # License info
        license_label = ttk.Label(main_frame, text="Released under the MIT License", font=("Segoe UI", 10))
        license_label.pack(pady=(0, PADDING["small"]))

        # Close button
        close_btn = ttk.Button(main_frame, text="Close", command=about_window.destroy)
        close_btn.pack(pady=(PADDING["medium"], 0))
    
    def show_license(self):
        """Display the application license in a dialog."""
        try:
            # Create license window
            license_window = tk.Toplevel(self.root)
            license_window.title("License")
            license_window.geometry("600x400")
            license_window.minsize(500, 300)
            license_window.transient(self.root)  # Set as transient to main window
            license_window.grab_set()  # Make modal
            
            # Try to set icon
            try:
                icon_path = get_resource_path(os.path.join("assets", "icon.ico"))
                if os.path.exists(icon_path):
                    license_window.iconbitmap(icon_path)
            except Exception as e:
                self.logger.warning(f"Could not set license window icon: {e}")
            
            # Main frame with padding
            main_frame = ttk.Frame(license_window, padding=PADDING["large"])
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Add title
            title_label = ttk.Label(main_frame, text="License", style="Header.TLabel")
            title_label.pack(pady=(0, PADDING["medium"]))
            
            # Create scrollable text area
            text_frame = ttk.Frame(main_frame)
            text_frame.pack(fill=tk.BOTH, expand=True, pady=PADDING["small"])
            
            # Add scrollbars
            y_scrollbar = ttk.Scrollbar(text_frame)
            y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Add text widget with scrollbar
            text_area = tk.Text(text_frame, wrap=tk.WORD, yscrollcommand=y_scrollbar.set, 
                               font=("Consolas", 10), padx=PADDING["small"], pady=PADDING["small"],
                               bg="white",
                               fg="black")
            text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            y_scrollbar.config(command=text_area.yview)
            
            # Read and display license content
            license_path = get_resource_path("LICENSE")
            if os.path.exists(license_path):
                with open(license_path, 'r') as f:
                    license_text = f.read()
                text_area.insert(tk.END, license_text)
            else:
                text_area.insert(tk.END, "License file not found.")
            
            # Make text read-only
            text_area.config(state=tk.DISABLED)
            
            # Add close button
            close_button = ttk.Button(main_frame, text="Close", command=license_window.destroy)
            close_button.pack(pady=PADDING["medium"])
            
            # Position the window relative to main window
            x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (600 // 2)
            y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (400 // 2)
            license_window.geometry(f"+{x}+{y}")
            
        except Exception as e:
            self.logger.error(f"Error showing license: {e}")
            messagebox.showerror("Error", f"Could not display license: {str(e)}")
    
    def increase_preview_font_size(self, event=None):
        """Increase the font size of the preview text."""
        current_size = self.preview_size_var.get()
        if current_size < 35:  # Set maximum size to 35
            self.preview_size_var.set(current_size + 1)
            self.preview_font(None)  # Update preview with new size
            # Save to config
            self.config['preview_size'] = self.preview_size_var.get()
            self.save_config()

    def decrease_preview_font_size(self, event=None):
        """Decrease the font size of the preview text."""
        current_size = self.preview_size_var.get()
        if current_size > 15:  # Set minimum size to 15
            self.preview_size_var.set(current_size - 1)
            self.preview_font(None)  # Update preview with new size
            # Save to config
            self.config['preview_size'] = self.preview_size_var.get()
            self.save_config()

    def reset_preview_font_size(self, event=None):
        """Reset the font size of the preview text to the default value."""
        self.preview_size_var.set(20)  # Set default size to 20
        self.preview_font(None)  # Update preview with new size
        # Save to config
        self.config['preview_size'] = 20
        self.save_config()
    
    def center_window(self):
        """Center the window on the screen."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def on_window_resize(self, event):
        """Handle window resize event."""
        # Only handle if the event is for the root window
        if event.widget == self.root:
            # Update the layout to fit the new window size
            self.root.update_idletasks()
    
    def close_application(self):
        """Properly close the application and release resources."""
        self.logger.info("Application closing", extra_context={"shutdown": True})
        
        # Perform cleanup
        self._cleanup_resources()
        
        # Save config before exit
        self.config['preview_size'] = self.preview_size_var.get()
        self.config['last_selected_font'] = self.font_var.get()
        self.save_config()
        
        # Destroy the root window
        self.root.destroy()
        
        # Ensure complete termination of the application
        sys.exit(0)
    
    def check_for_updates(self):
        """Check for updates and notify the user if available."""
        self.logger.info("Checking for updates...")
        self.status_var.set("Checking for updates...")

        from src.utilities.version_manager import version_manager

        def update_status(update_available):
            if version_manager.last_error:
                self.logger.error(f"Update check error: {version_manager.last_error}")
                self.status_var.set("Update check failed")
                if "Network error" in version_manager.last_error:
                    user_msg = (
                        "Could not check for updates due to a network error.\n\n"
                        "Please check your internet connection and try again."
                    )
                else:
                    user_msg = "Could not check for updates due to an unexpected error."
                self.root.after(0, lambda: messagebox.showerror("Update Check Failed", user_msg))
            elif update_available:
                self.logger.info("Update available.")
                self.status_var.set("Update available")
                self.root.after(0, version_manager._show_update_message)
            else:
                self.logger.info("No updates available.")
                self.status_var.set("No updates available")
                # Show info dialog on main thread (manual check only)
                self.root.after(0, lambda: messagebox.showinfo("No Updates", "You are using the latest version of FontEase."))

        version_manager.check_for_updates(auto_check=False, callback=update_status)

    def silent_update_check(self):
        """Silently check for updates and show dialog only if available."""
        from src.utilities.version_manager import version_manager
        def update_status(update_available):
            if version_manager.last_error:
                # Do not show error dialog for silent/background checks
                return
            if update_available:
                self.root.after(0, version_manager._show_update_message)
            # Do nothing if no update is available
        version_manager.check_for_updates(auto_check=True, callback=update_status)
    
    def load_config(self):
        """Load configuration from the config file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    try:
                        return json.load(f)
                    except json.JSONDecodeError:
                        # File exists but is empty or corrupted, reset to empty config
                        self.logger.warning("Config file empty or corrupted. Resetting to defaults.")
                        config = {}
                        with open(self.config_path, 'w', encoding='utf-8') as fw:
                            json.dump(config, fw, indent=4)
                        return config
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}", exc_info=True)
        # If file does not exist or error, ensure file exists with empty config
        config = {}
        try:
            with open(self.config_path, 'w', encoding='utf-8') as fw:
                json.dump(config, fw, indent=4)
        except Exception as e:
            self.logger.error(f"Failed to write default config: {e}", exc_info=True)
        return config

    def save_config(self):
        """Save configuration to the config file."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}", exc_info=True)

    def validate_config(self, config, all_fonts=None):
        """Validate and repair the configuration."""
        changed = False
        # Validate preview_size
        if (
            'preview_size' not in config or
            not isinstance(config['preview_size'], int) or
            not (15 <= config['preview_size'] <= 35)
        ):
            config['preview_size'] = 20
            changed = True

        # Validate last_selected_font
        if 'last_selected_font' not in config or not isinstance(config['last_selected_font'], str):
            config['last_selected_font'] = ''
            changed = True
        elif all_fonts is not None and config['last_selected_font'] not in all_fonts:
            config['last_selected_font'] = ''
            changed = True

        if changed:
            self.logger.info("Config auto-repaired due to invalid or missing values.", extra_context={"config": config})
            self.save_config()
        return config