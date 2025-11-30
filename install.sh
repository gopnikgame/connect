#!/bin/bash

# =============================================================================
# MyGit Installer Script
# Script for installing the private GitHub repository connector
# Designed for Ubuntu server operating systems
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Installation paths
INSTALL_DIR="/opt/mygit"
CONFIG_DIR="$HOME/.mygit"
CONFIG_FILE="$CONFIG_DIR/config.json"
BIN_LINK="/usr/local/bin/mygit"

# Print colored message
print_msg() {
    local color=$1
    local msg=$2
    echo -e "${color}${msg}${NC}"
}

# Print header
print_header() {
    echo ""
    print_msg "$BLUE" "=============================================="
    print_msg "$BLUE" "      MyGit - Private Repository Connector     "
    print_msg "$BLUE" "=============================================="
    echo ""
}

# Check if running as root for system-wide installation
check_permissions() {
    if [[ $EUID -ne 0 ]]; then
        print_msg "$YELLOW" "Warning: Not running as root. Will attempt local installation."
        INSTALL_DIR="$HOME/.local/share/mygit"
        BIN_LINK="$HOME/.local/bin/mygit"
        mkdir -p "$HOME/.local/bin"
        # Add to PATH if not already there
        if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
            print_msg "$YELLOW" "Adding $HOME/.local/bin to PATH in ~/.bashrc"
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
        fi
    fi
}

# Check for required dependencies
check_dependencies() {
    print_msg "$BLUE" "Checking dependencies..."
    
    local missing_deps=()
    
    # Check for git
    if ! command -v git &> /dev/null; then
        missing_deps+=("git")
    fi
    
    # Check for python3
    if ! command -v python3 &> /dev/null; then
        missing_deps+=("python3")
    fi
    
    # Check for pip3
    if ! command -v pip3 &> /dev/null; then
        missing_deps+=("python3-pip")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        print_msg "$RED" "Missing dependencies: ${missing_deps[*]}"
        print_msg "$YELLOW" "Please install them using:"
        print_msg "$YELLOW" "  sudo apt update && sudo apt install -y ${missing_deps[*]}"
        exit 1
    fi
    
    print_msg "$GREEN" "All dependencies are installed."
}

# Prompt for GitHub credentials
get_credentials() {
    print_msg "$BLUE" "Configuring GitHub access..."
    echo ""
    
    # GitHub username
    read -p "Enter your GitHub username: " github_username
    if [[ -z "$github_username" ]]; then
        print_msg "$RED" "Error: GitHub username cannot be empty."
        exit 1
    fi
    
    # GitHub Personal Access Token
    echo ""
    print_msg "$YELLOW" "You need a GitHub Personal Access Token (PAT) with 'repo' scope."
    print_msg "$YELLOW" "Create one at: https://github.com/settings/tokens"
    echo ""
    read -sp "Enter your GitHub Personal Access Token: " github_token
    echo ""
    
    if [[ -z "$github_token" ]]; then
        print_msg "$RED" "Error: GitHub token cannot be empty."
        exit 1
    fi
    
    # Default clone directory
    echo ""
    read -p "Enter default directory for cloning repositories [$HOME/mygit-repos]: " clone_dir
    clone_dir=${clone_dir:-"$HOME/mygit-repos"}
}

# Save configuration
save_config() {
    print_msg "$BLUE" "Saving configuration..."
    
    # Create config directory
    mkdir -p "$CONFIG_DIR"
    chmod 700 "$CONFIG_DIR"
    
    # Create clone directory
    mkdir -p "$clone_dir"
    
    # Save config as JSON using Python for proper escaping
    python3 -c "
import json
import sys

config = {
    'github_username': sys.argv[1],
    'github_token': sys.argv[2],
    'clone_directory': sys.argv[3]
}

with open(sys.argv[4], 'w') as f:
    json.dump(config, f, indent=4)
" "$github_username" "$github_token" "$clone_dir" "$CONFIG_FILE"
    
    # Secure the config file
    chmod 600 "$CONFIG_FILE"
    
    print_msg "$GREEN" "Configuration saved to $CONFIG_FILE"
}

# Install the main Python program
install_program() {
    print_msg "$BLUE" "Installing MyGit..."
    
    # Create installation directory
    mkdir -p "$INSTALL_DIR"
    
    # Get the directory where install.sh is located
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    
    # Copy the Python program
    if [[ -f "$SCRIPT_DIR/mygit.py" ]]; then
        cp "$SCRIPT_DIR/mygit.py" "$INSTALL_DIR/mygit.py"
        chmod +x "$INSTALL_DIR/mygit.py"
    else
        print_msg "$RED" "Error: mygit.py not found in $SCRIPT_DIR"
        exit 1
    fi
    
    # Create symlink
    if [[ -L "$BIN_LINK" ]] || [[ -e "$BIN_LINK" ]]; then
        rm -f "$BIN_LINK"
    fi
    ln -s "$INSTALL_DIR/mygit.py" "$BIN_LINK"
    
    print_msg "$GREEN" "MyGit installed successfully!"
    print_msg "$GREEN" "Symlink created at: $BIN_LINK"
}

# Print usage instructions
print_usage() {
    echo ""
    print_msg "$GREEN" "=============================================="
    print_msg "$GREEN" "            Installation Complete!             "
    print_msg "$GREEN" "=============================================="
    echo ""
    print_msg "$BLUE" "Usage:"
    echo "  mygit clone <owner/repo>     - Clone a private repository"
    echo "  mygit run <owner/repo> <script.sh> - Clone and run a script"
    echo "  mygit list                   - List cloned repositories"
    echo "  mygit config                 - Show current configuration"
    echo "  mygit help                   - Show help message"
    echo ""
    if [[ $EUID -ne 0 ]]; then
        print_msg "$YELLOW" "Note: You may need to restart your terminal or run:"
        print_msg "$YELLOW" "  source ~/.bashrc"
        print_msg "$YELLOW" "to use the 'mygit' command."
    fi
}

# Main installation process
main() {
    print_header
    check_permissions
    check_dependencies
    get_credentials
    save_config
    install_program
    print_usage
}

# Run main function
main
