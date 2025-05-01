"""
Font management module for interacting with Windows fonts and registry.
"""

import os
import sys
import tempfile
import shutil
import winreg
from tkinter import font, messagebox, filedialog
import win32api
import win32con
import win32event
import win32process
from win32comext.shell import shellcon
from win32comext.shell.shell import ShellExecuteEx
from typing import List, Tuple, Optional, Dict, Any, Union
from fontTools.ttLib import TTFont

from src.utilities.logger import AppLogger

logger = AppLogger()

def get_installed_fonts() -> List[str]:
    """Get a list of all installed fonts in the system
    
    Returns:
        List[str]: Sorted list of font family names
    """
    try:
        # Get all installed fonts in Windows
        all_fonts = sorted(list(set(font.families())))
        return all_fonts
    except Exception as e:
        logger.error(f"Failed to load fonts: {str(e)}", exc_info=True, extra_context={"operation": "get_installed_fonts"})
        return []

def detect_current_system_font() -> str:
    """Detect the current system font from registry
    
    Returns:
        str: The name of the current system font, or 'Segoe UI' if not detected
    """
    try:
        # Open the registry key where font substitutions are stored
        key_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\FontSubstitutes"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            try:
                # Try to read the Segoe UI value
                font_name, _ = winreg.QueryValueEx(key, "Segoe UI")
                return font_name
            except FileNotFoundError:
                # If the value doesn't exist, it's likely the default Segoe UI
                return "Segoe UI"
            except Exception as e:
                logger.error(f"Error reading registry value: {str(e)}", exc_info=True, extra_context={"operation": "detect_current_system_font", "stage": "read_registry_value"})
                return "Segoe UI"  # Assume default if can't detect
    except Exception as e:
        logger.error(f"Error opening registry key: {str(e)}", exc_info=True, extra_context={"operation": "detect_current_system_font", "stage": "open_registry_key"})
        return "Segoe UI"  # Assume default if can't detect

def generate_registry_file(font_name: str, temp_dir: Optional[str] = None) -> Optional[str]:
    """Generate the registry file content for font replacement
    
    Args:
        font_name: The name of the font to set as system font
        temp_dir: Directory to create the temporary registry file in (default: system temp)
        
    Returns:
        Optional[str]: Path to the generated registry file, or None on failure
    """
    try:
        reg_content = "Windows Registry Editor Version 5.00\n\n"
        
        # Add Fonts section
        reg_content += "[HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Fonts]\n"
        reg_content += '"Segoe UI (TrueType)"=""\n'
        reg_content += '"Segoe UI Bold (TrueType)"=""\n'
        reg_content += '"Segoe UI Bold Italic (TrueType)"=""\n'
        reg_content += '"Segoe UI Italic (TrueType)"=""\n'
        reg_content += '"Segoe UI Light (TrueType)"=""\n'
        reg_content += '"Segoe UI Semibold (TrueType)"=""\n'
        reg_content += '"Segoe UI Symbol (TrueType)"=""\n\n'
        
        # Add FontSubstitutes section
        reg_content += "[HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\FontSubstitutes]\n"
        reg_content += f'"Segoe UI"="{font_name}"\n'
        
        # Use provided temp_dir or fallback to system temp
        mkstemp_kwargs = {'suffix': '.reg'}
        if temp_dir is not None:
            mkstemp_kwargs['dir'] = temp_dir
        fd, temp_path = tempfile.mkstemp(**mkstemp_kwargs)
        os.close(fd)
        
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(reg_content)
        
        return temp_path
    except Exception as e:
        logger.error(f"Failed to generate registry file: {str(e)}", exc_info=True, extra_context={"operation": "generate_registry_file", "font_name": font_name})
        return None

def apply_system_font(font_name: str, temp_dir: Optional[str] = None) -> bool:
    """Apply the selected font as the Windows system font.
    
    Args:
        font_name: The name of the font to apply
        temp_dir: Directory to create the temporary registry file in (default: system temp)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Generate registry file
        reg_file_path = generate_registry_file(font_name, temp_dir=temp_dir)
        
        # Apply registry file
        if not reg_file_path:
            raise Exception("Failed to generate registry file")
        
        # Use ShellExecuteEx to run regedit with admin privileges
        params = f'/s "{reg_file_path}"'
        result = ShellExecuteEx(
            nShow=win32con.SW_HIDE,
            fMask=shellcon.SEE_MASK_NOCLOSEPROCESS,
            lpVerb='runas',
            lpFile='regedit.exe',
            lpParameters=params
        )
        procHandle = result['hProcess']
        win32event.WaitForSingleObject(procHandle, 10000)  # 10 second timeout
        exit_code = win32process.GetExitCodeProcess(procHandle)
        
        # Clean up registry file
        try:
            os.remove(reg_file_path)
        except Exception as e:
            logger.error(f"Error removing temp file: {str(e)}", exc_info=True, extra_context={"file": reg_file_path})
        
        return True
    except Exception as e:
        logger.error(f"Failed to apply font: {str(e)}", exc_info=True, extra_context={"operation": "apply_system_font", "font_name": font_name})
        return False

def reset_system_font(temp_dir: Optional[str] = None) -> bool:
    """Reset the Windows system font to the default Segoe UI.
    
    Args:
        temp_dir: Directory to create the temporary registry file in (default: system temp)
        
    Returns:
        bool: True if successful, False otherwise
    """
    return apply_system_font("Segoe UI", temp_dir=temp_dir)

def get_font_family_name(font_path: str) -> Optional[str]:
    """Extract font family name from a TTF/OTF file using fontTools.
    
    Args:
        font_path: Path to the font file
        
    Returns:
        Optional[str]: Family name of the font, or None if not found
    """
    try:
        with TTFont(font_path) as tt:
            # Get the 'name' table
            names = tt.get('name')
            if not names:
                return None
                
            # Look for family name (nameID 1)
            for record in names.names:
                if record.nameID == 1:  # Family name
                    if record.isUnicode():
                        return record.toUnicode()
                    else:
                        return record.string.decode('utf-8', errors='ignore')
                        
            # Fallback to font filename without extension
            return os.path.splitext(os.path.basename(font_path))[0]
    except Exception as e:
        logger.error(f"Error extracting font name from {font_path}: {str(e)}", exc_info=True, extra_context={"operation": "get_font_family_name", "font_path": font_path})
        return os.path.splitext(os.path.basename(font_path))[0]

def install_font(font_paths: Optional[List[str]] = None) -> Tuple[int, List[str]]:
    """Install TTF/OTF font files to the Windows Fonts directory.
    
    This method allows users to select and install font files. It attempts multiple
    installation methods with fallbacks for different permission scenarios:
    1. Direct file copy (if user has write access to Fonts directory)
    2. Elevated batch file execution (for admin privileges)
    
    Args:
        font_paths: List of paths to font files to install, or None to prompt user
        
    Returns:
        Tuple[int, List[str]]: Number of successfully installed fonts
                               and list of failed font filenames
    """
    if font_paths is None:
        # Ask user to select font files
        filetypes = [("Font Files", "*.ttf *.otf"), ("All Files", "*.*")]
        font_paths = filedialog.askopenfilenames(title="Select Font Files", filetypes=filetypes)
        
    if not font_paths:
        return 0, []  # User canceled
    
    # Get Windows Fonts directory
    fonts_dir = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')
    
    # Initialize counters for success/failure reporting
    success_count = 0
    failed_fonts = []
    
    # Try to install each selected font
    for font_path in font_paths:
        try:
            # Extract font filename
            font_filename = os.path.basename(font_path)
            dest_path = os.path.join(fonts_dir, font_filename)
            
            # Method 1: Try direct file copy first (works if user has permissions)
            try:
                # Copy font file to Windows Fonts directory
                shutil.copy2(font_path, dest_path)
                
                # Register font in Windows registry
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts', 0, winreg.KEY_SET_VALUE) as key:
                    # Get font name from file
                    font_name = get_font_family_name(font_path)
                    if font_name:
                        winreg.SetValueEx(key, f"{font_name} (TrueType)", 0, winreg.REG_SZ, font_filename)
                
                # Font installed successfully
                success_count += 1
                continue
                
            except (PermissionError, OSError):
                # If direct copy fails, try method 2
                pass
            
            # Method 2: Create and execute a batch file with elevated privileges
            # Create a temporary batch file
            fd, batch_path = tempfile.mkstemp(suffix='.bat')
            os.close(fd)
            
            # Write commands to batch file
            with open(batch_path, 'w') as f:
                f.write('@echo off\n')
                f.write('echo Installing font: %s\n' % font_filename)
                f.write('copy /y "%s" "%s"\n' % (font_path.replace('/', '\\'), dest_path.replace('/', '\\')))
                
                # Add registry command
                # Get font name from file
                try:
                    font_name = get_font_family_name(font_path)
                    if font_name:
                        f.write('reg add "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Fonts" /v "%s (TrueType)" /t REG_SZ /d "%s" /f\n' % 
                               (font_name, font_filename))
                except Exception:
                    # If we can't get the font name, use the filename without extension
                    font_name = os.path.splitext(font_filename)[0]
                    f.write('reg add "HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Fonts" /v "%s (TrueType)" /t REG_SZ /d "%s" /f\n' % 
                           (font_name, font_filename))
            
            # Execute batch file with admin privileges
            try:
                # Use ShellExecuteEx to run with admin privileges
                result = ShellExecuteEx(nShow=win32con.SW_HIDE,
                                       fMask=shellcon.SEE_MASK_NOCLOSEPROCESS,
                                       lpVerb='runas',
                                       lpFile='cmd.exe',
                                       lpParameters='/c "' + batch_path + '"')
                
                # Wait for process to complete
                win32event.WaitForSingleObject(result['hProcess'], 10000)  # 10 second timeout
                win32process.GetExitCodeProcess(result['hProcess'])
                
                # Check if font file exists in destination
                if os.path.exists(dest_path):
                    success_count += 1
                else:
                    failed_fonts.append(font_filename)
                    
            except Exception as e:
                failed_fonts.append(font_filename)
                logger.error(f"Error installing font {font_filename}: {str(e)}", exc_info=True, extra_context={"operation": "install_font", "font": font_filename})
            
            # Clean up batch file
            try:
                os.unlink(batch_path)
            except:
                pass
                
        except Exception as e:
            failed_fonts.append(os.path.basename(font_path))
            logger.error(f"Error installing font {os.path.basename(font_path)}: {str(e)}", exc_info=True, extra_context={"operation": "install_font", "font": os.path.basename(font_path)})
    
    return success_count, failed_fonts

def open_windows_fonts_folder() -> bool:
    """Open the Windows Fonts folder
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        fonts_folder = os.path.join(os.environ['WINDIR'], 'Fonts')
        os.startfile(fonts_folder)
        return True
    except Exception as e:
        logger.error(f"Failed to open Windows Fonts folder: {str(e)}")
        return False 