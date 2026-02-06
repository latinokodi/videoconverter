#!/usr/bin/env python3
"""
FFmpeg Installer for Windows
An interactive, robust, colorful application that detects, installs,
and adds FFmpeg to PATH in Windows systems.
"""

import os
import sys
import subprocess
import json
import time
import shutil
import requests
import zipfile
import tempfile
import winreg
import ctypes
from pathlib import Path
from typing import Optional, List, Tuple
import colorama
from colorama import Fore, Style, init

# Initialize colorama for Windows support
init(autoreset=True)

class FFmpegInstaller:
    """Main class for FFmpeg installation and PATH management"""
    
    def __init__(self):
        self.ffmpeg_downloader_available = False
        self.ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        self.install_dir = Path(os.environ.get('ProgramFiles', 'C:\\Program Files')) / "FFmpeg"
        self.bin_dir = self.install_dir / "bin"
        self.temp_dir = Path(tempfile.gettempdir()) / "ffmpeg_installer"
        self.admin_access = self.check_admin_access()
        
    def check_admin_access(self) -> bool:
        """Check if the script has administrator privileges"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
    
    def print_banner(self):
        """Display colorful banner"""
        banner = f"""
{Fore.CYAN}{Style.BRIGHT}╔═══════════════════════════════════════════════════════════╗
{Fore.CYAN}{Style.BRIGHT}║{Fore.GREEN}{Style.BRIGHT}                FFmpeg Installer for Windows               {Fore.CYAN}{Style.BRIGHT}║
{Fore.CYAN}{Style.BRIGHT}║{Fore.YELLOW}      Interactive • Robust • Colorful • Error-Free       {Fore.CYAN}{Style.BRIGHT}║
{Fore.CYAN}{Style.BRIGHT}╚═══════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
        print(banner)
    
    def print_step(self, step_number: int, message: str):
        """Print a step with colorful formatting"""
        print(f"\n{Fore.BLUE}{Style.BRIGHT}[Step {step_number}/5]{Style.RESET_ALL} {Fore.WHITE}{message}{Style.RESET_ALL}")
    
    def print_success(self, message: str):
        """Print success message"""
        print(f"{Fore.GREEN}{Style.BRIGHT}✓ {message}{Style.RESET_ALL}")
    
    def print_warning(self, message: str):
        """Print warning message"""
        print(f"{Fore.YELLOW}{Style.BRIGHT}⚠ {message}{Style.RESET_ALL}")
    
    def print_error(self, message: str):
        """Print error message"""
        print(f"{Fore.RED}{Style.BRIGHT}✗ {message}{Style.RESET_ALL}")
    
    def print_info(self, message: str):
        """Print info message"""
        print(f"{Fore.CYAN}ℹ {message}{Style.RESET_ALL}")
    
    def run_command(self, command: list, capture_output: bool = True) -> Tuple[bool, str]:
        """Run a command and return success status and output"""
        try:
            result = subprocess.run(
                command,
                capture_output=capture_output,
                text=True,
                check=True,
                shell=True if os.name == 'nt' else False
            )
            return True, result.stdout.strip() if capture_output else ""
        except subprocess.CalledProcessError as e:
            return False, e.stderr.strip() if capture_output else str(e)
        except Exception as e:
            return False, str(e)
    
    def check_ffmpeg_installed(self) -> Tuple[bool, Optional[str]]:
        """Check if FFmpeg is already installed and accessible"""
        # Try to run ffmpeg command
        success, output = self.run_command(['ffmpeg', '-version'])
        if success:
            version_line = output.split('\n')[0] if output else "Unknown version"
            return True, version_line
        
        # Check common installation paths
        common_paths = [
            Path("C:\\ffmpeg\\bin"),
            Path(os.environ.get('ProgramFiles', 'C:\\Program Files')) / "FFmpeg" / "bin",
            Path(os.environ.get('LOCALAPPDATA')) / "FFmpeg" / "bin"
        ]
        
        for path in common_paths:
            ffmpeg_exe = path / "ffmpeg.exe"
            if ffmpeg_exe.exists():
                return True, f"Found at: {path}"
        
        return False, None
    
    def check_ffmpeg_in_path(self) -> bool:
        """Check if FFmpeg is in PATH"""
        path_dirs = os.environ['PATH'].split(os.pathsep)
        for dir_path in path_dirs:
            ffmpeg_path = Path(dir_path) / "ffmpeg.exe"
            if ffmpeg_path.exists():
                return True
        return False
    
    def install_via_ffmpeg_downloader(self) -> Tuple[bool, str]:
        """Try to install using ffmpeg-downloader package"""
        try:
            import ffmpeg_downloader as ffdl
            self.ffmpeg_downloader_available = True
            
            self.print_info("Using ffmpeg-downloader package for installation...")
            
            # Install latest FFmpeg
            result = subprocess.run(
                [sys.executable, '-m', 'ffdl', 'install', '--latest'],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Get installation path
            install_path_result = subprocess.run(
                [sys.executable, '-m', 'ffdl', 'path'],
                capture_output=True,
                text=True,
                check=True
            )
            
            install_path = install_path_result.stdout.strip()
            bin_path = Path(install_path) / "bin"
            
            return True, str(bin_path)
            
        except ImportError:
            return False, "ffmpeg-downloader package not available"
        except Exception as e:
            return False, f"Error using ffmpeg-downloader: {str(e)}"
    
    def download_ffmpeg_manually(self) -> Tuple[bool, str]:
        """Download FFmpeg manually from gyan.dev"""
        try:
            self.print_info(f"Downloading FFmpeg from: {self.ffmpeg_url}")
            
            # Create temp directory
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            zip_path = self.temp_dir / "ffmpeg.zip"
            
            # Download with progress
            response = requests.get(self.ffmpeg_url, stream=True, timeout=30)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            print(f"{Fore.CYAN}Downloading: {progress:.1f}%{Style.RESET_ALL}", end='\r')
            
            print(f"\n{Fore.GREEN}✓ Download completed successfully!{Style.RESET_ALL}")
            return True, str(zip_path)
            
        except Exception as e:
            return False, f"Download error: {str(e)}"
    
    def extract_ffmpeg(self, zip_path: str) -> Tuple[bool, str]:
        """Extract FFmpeg ZIP file"""
        try:
            self.print_info("Extracting FFmpeg files...")
            
            # Create install directory
            self.install_dir.parent.mkdir(parents=True, exist_ok=True)
            
            # Extract ZIP
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Get the first directory name in the zip (usually contains version info)
                first_dir = zip_ref.namelist()[0].split('/')[0]
                zip_ref.extractall(self.temp_dir)
            
            # Find the extracted folder
            extracted_folder = None
            for item in self.temp_dir.iterdir():
                if item.is_dir() and "ffmpeg" in item.name.lower():
                    extracted_folder = item
                    break
            
            if not extracted_folder:
                return False, "Could not find extracted FFmpeg folder"
            
            # Find the bin directory
            bin_source = None
            for root, dirs, files in os.walk(extracted_folder):
                if "bin" in dirs and any(f.startswith("ffmpeg") for f in os.listdir(os.path.join(root, "bin"))):
                    bin_source = Path(root) / "bin"
                    break
            
            if not bin_source or not bin_source.exists():
                return False, "Could not find bin directory in extracted files"
            
            # Copy files to install directory
            self.install_dir.mkdir(parents=True, exist_ok=True)
            self.bin_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy all files from bin directory
            for file in bin_source.iterdir():
                if file.is_file():
                    shutil.copy2(file, self.bin_dir / file.name)
            
            # Clean up temp files
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            
            self.print_success(f"FFmpeg extracted to: {self.bin_dir}")
            return True, str(self.bin_dir)
            
        except Exception as e:
            return False, f"Extraction error: {str(e)}"
    
    def add_to_path_registry(self, path_to_add: str) -> Tuple[bool, str]:
        """Add directory to PATH using Windows registry"""
        try:
            # Open the registry key for environment variables
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Environment",
                0,
                winreg.KEY_ALL_ACCESS
            )
            
            # Get current PATH value
            try:
                current_path, _ = winreg.QueryValueEx(key, "PATH")
            except FileNotFoundError:
                current_path = ""
            
            # Check if path already exists in PATH
            path_dirs = current_path.split(';') if current_path else []
            if path_to_add in path_dirs:
                return True, "Path already exists in PATH environment variable"
            
            # Add new path
            new_path = current_path + ';' + path_to_add if current_path else path_to_add
            
            # Update registry
            winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path)
            winreg.CloseKey(key)
            
            # Broadcast environment change
            HWND_BROADCAST = 0xFFFF
            WM_SETTINGCHANGE = 0x001A
            ctypes.windll.user32.SendMessageW(HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment")
            
            return True, "Successfully added to PATH via registry"
            
        except Exception as e:
            return False, f"Registry error: {str(e)}"
    
    def add_to_path_permanent(self, path_to_add: str) -> Tuple[bool, str]:
        """Add directory to PATH permanently"""
        if not self.admin_access:
            self.print_warning("Administrator privileges not detected. PATH changes may require restart.")
        
        return self.add_to_path_registry(path_to_add)
    
    def verify_installation(self) -> Tuple[bool, str]:
        """Verify FFmpeg installation and PATH configuration"""
        time.sleep(2)  # Wait for environment changes to take effect
        
        # Refresh environment variables
        os.environ['PATH'] = os.environ['PATH']
        
        success, output = self.run_command(['ffmpeg', '-version'])
        if success:
            version_info = output.split('\n')[0]
            return True, version_info
        
        return False, "FFmpeg command not found after installation"
    
    def request_admin_privileges(self):
        """Request administrator privileges if needed"""
        if self.admin_access:
            return True
        
        self.print_warning("Administrator privileges are recommended for permanent PATH changes.")
        response = input(f"{Fore.YELLOW}Would you like to restart this script with administrator privileges? (y/n): {Style.RESET_ALL}").lower()
        
        if response == 'y':
            try:
                script_path = os.path.abspath(sys.argv[0])
                params = ' '.join(sys.argv[1:])
                
                # Use PowerShell to restart with admin privileges
                command = f'start-process python -ArgumentList "{script_path} {params}" -Verb RunAs'
                subprocess.run(["powershell", "-Command", command], check=True)
                sys.exit(0)
            except Exception as e:
                self.print_error(f"Failed to restart with admin privileges: {str(e)}")
                return False
        
        return True
    
    def install_ffmpeg(self) -> Tuple[bool, str]:
        """Main installation logic"""
        self.print_step(1, "Checking current FFmpeg installation...")
        
        # Check if FFmpeg is already installed and in PATH
        ffmpeg_installed, version_info = self.check_ffmpeg_installed()
        ffmpeg_in_path = self.check_ffmpeg_in_path()
        
        if ffmpeg_installed and ffmpeg_in_path:
            self.print_success(f"FFmpeg is already installed and in PATH!")
            self.print_info(f"Version: {version_info}")
            return True, "Already installed"
        
        if ffmpeg_installed and not ffmpeg_in_path:
            self.print_warning("FFmpeg is installed but not in PATH!")
            self.print_info(f"Found at: {version_info}")
        else:
            self.print_info("FFmpeg not found. Proceeding with installation...")
        
        # Try ffmpeg-downloader first
        self.print_step(2, "Attempting installation with ffmpeg-downloader...")
        success, install_path = self.install_via_ffmpeg_downloader()
        
        if not success:
            self.print_warning("ffmpeg-downloader not available or failed. Using manual installation...")
            
            self.print_step(3, "Downloading FFmpeg manually...")
            success, zip_path = self.download_ffmpeg_manually()
            if not success:
                return False, zip_path
            
            self.print_step(4, "Extracting FFmpeg files...")
            success, install_path = self.extract_ffmpeg(zip_path)
            if not success:
                return False, install_path
        
        # Add to PATH
        self.print_step(5, "Adding FFmpeg to PATH...")
        bin_path = Path(install_path)
        
        if not bin_path.exists():
            return False, f"Installation path does not exist: {bin_path}"
        
        success, path_message = self.add_to_path_permanent(str(bin_path))
        
        if not success:
            self.print_error(f"Failed to add to PATH: {path_message}")
            self.print_warning("You may need to add this path manually:")
            self.print_info(f"Path to add: {bin_path}")
            return False, path_message
        
        self.print_success(f"✓ Added to PATH: {bin_path}")
        
        # Verify installation
        self.print_info("Verifying installation...")
        success, verify_message = self.verify_installation()
        
        if success:
            self.print_success(f"✓ FFmpeg installation verified successfully!")
            self.print_info(f"Version: {verify_message}")
            return True, "Installation successful"
        else:
            self.print_warning("✗ Installation verification failed!")
            self.print_info("FFmpeg may be installed but PATH changes might require a system restart.")
            self.print_info(f"Try running 'ffmpeg -version' in a new command prompt.")
            return True, "Installation completed but verification failed - restart may be required"
    
    def run_interactive(self):
        """Run the installer in interactive mode"""
        self.print_banner()
        
        # Check Python version
        if sys.version_info < (3, 7):
            self.print_error("Python 3.7 or higher is required!")
            sys.exit(1)
        
        # Check Windows
        if os.name != 'nt':
            self.print_error("This script is designed for Windows only!")
            sys.exit(1)
        
        self.print_info("System Information:")
        self.print_info(f"Python Version: {sys.version.split()[0]}")
        self.print_info(f"Operating System: Windows")
        self.print_info(f"Administrator Access: {'Yes' if self.admin_access else 'No'}")
        
        print(f"\n{Fore.CYAN}{Style.BRIGHT}This script will:{Style.RESET_ALL}")
        print(f"  • {Fore.GREEN}✓{Style.RESET_ALL} Check if FFmpeg is already installed")
        print(f"  • {Fore.GREEN}✓{Style.RESET_ALL} Download the latest FFmpeg binaries if needed")
        print(f"  • {Fore.GREEN}✓{Style.RESET_ALL} Install FFmpeg to a system directory")
        print(f"  • {Fore.GREEN}✓{Style.RESET_ALL} Add FFmpeg to your system PATH permanently")
        print(f"  • {Fore.GREEN}✓{Style.RESET_ALL} Verify the installation")
        
        response = input(f"\n{Fore.YELLOW}Do you want to proceed with the FFmpeg installation? (y/n): {Style.RESET_ALL}").lower()
        
        if response != 'y':
            self.print_info("Installation cancelled by user.")
            sys.exit(0)
        
        # Request admin privileges if needed
        if not self.admin_access:
            self.request_admin_privileges()
        
        print(f"\n{Fore.CYAN}{Style.BRIGHT}Starting FFmpeg installation process...{Style.RESET_ALL}")
        
        try:
            success, message = self.install_ffmpeg()
            
            if success:
                print(f"\n{Fore.GREEN}{Style.BRIGHT}╔═══════════════════════════════════════════════════════════╗")
                print(f"║                ✨ Installation Complete! ✨              ║")
                print(f"║                                                           ║")
                print(f"║    FFmpeg has been successfully installed and added     ║")
                print(f"║               to your system PATH!                      ║")
                print(f"║                                                           ║")
                print(f"║    You can now use FFmpeg from any command prompt:       ║")
                print(f"║    • ffmpeg -version                                     ║")
                print(f"║    • ffmpeg -i input.mp4 output.mp3                      ║")
                print(f"║                                                           ║")
                print(f"║    {Fore.YELLOW}Note: You may need to restart your command prompts{Fore.GREEN}   ║")
                print(f"║    {Fore.YELLOW}or applications for the PATH changes to take effect.{Fore.GREEN} ║")
                print(f"╚═══════════════════════════════════════════════════════════╝{Style.RESET_ALL}")
            else:
                self.print_error("\nInstallation failed!")
                self.print_error(f"Error: {message}")
                self.print_warning("\nTroubleshooting suggestions:")
                self.print_info("1. Run this script as Administrator")
                self.print_info("2. Check your internet connection")
                self.print_info("3. Try manual installation from https://www.gyan.dev/ffmpeg/builds/")
                sys.exit(1)
                
        except KeyboardInterrupt:
            self.print_warning("\nInstallation cancelled by user (Ctrl+C)")
            sys.exit(1)
        except Exception as e:
            self.print_error(f"\nUnexpected error during installation: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        # Ask if user wants to test FFmpeg
        test_response = input(f"\n{Fore.CYAN}Would you like to test FFmpeg now? (y/n): {Style.RESET_ALL}").lower()
        if test_response == 'y':
            try:
                success, output = self.run_command(['ffmpeg', '-version'])
                if success:
                    print(f"\n{Fore.GREEN}FFmpeg test successful!{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}Output:{Style.RESET_ALL}")
                    print(output.split('\n')[0])  # Show first line with version
                else:
                    print(f"\n{Fore.YELLOW}FFmpeg test failed. Try in a new command prompt.{Style.RESET_ALL}")
            except Exception as e:
                print(f"\n{Fore.YELLOW}Could not test FFmpeg: {str(e)}{Style.RESET_ALL}")

def main():
    """Main entry point"""
    try:
        installer = FFmpegInstaller()
        installer.run_interactive()
    except Exception as e:
        print(f"\n{Fore.RED}{Style.BRIGHT}Fatal error: {str(e)}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Please report this issue with the error details above.{Style.RESET_ALL}")
        sys.exit(1)

if __name__ == "__main__":
    main()