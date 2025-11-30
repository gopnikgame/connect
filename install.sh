#!/bin/bash

# =============================================================================
# MyGit Installer Script
# Скрипт установки коннектора приватных репозиториев
# Разработан для операционных систем Ubuntu server
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
    print_msg "$BLUE" "   MyGit - Коннектор приватных репозиториев   "
    print_msg "$BLUE" "=============================================="
    echo ""
}

# Check if running as root for system-wide installation
check_permissions() {
    if [[ $EUID -ne 0 ]]; then
        print_msg "$YELLOW" "Внимание: Скрипт запущен без прав root. Будет выполнена локальная установка."
        INSTALL_DIR="$HOME/.local/share/mygit"
        BIN_LINK="$HOME/.local/bin/mygit"
        mkdir -p "$HOME/.local/bin"
        # Add to PATH if not already there
        if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
            print_msg "$YELLOW" "Добавление $HOME/.local/bin в PATH в ~/.bashrc"
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
        fi
    fi
}

# Check for required dependencies
check_dependencies() {
    print_msg "$BLUE" "Проверка зависимостей..."
    
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
        print_msg "$RED" "Отсутствуют зависимости: ${missing_deps[*]}"
        print_msg "$YELLOW" "Пожалуйста, установите их используя:"
        print_msg "$YELLOW" "  sudo apt update && sudo apt install -y ${missing_deps[*]}"
        exit 1
    fi
    
    print_msg "$GREEN" "Все зависимости установлены."
}

# Prompt for GitHub credentials
get_credentials() {
    print_msg "$BLUE" "Настройка доступа к GitHub..."
    echo ""
    
    # GitHub username
    read -p "Введите ваше имя пользователя GitHub: " github_username
    if [[ -z "$github_username" ]]; then
        print_msg "$RED" "Ошибка: Имя пользователя GitHub не может быть пустым."
        exit 1
    fi
    
    # GitHub Personal Access Token
    echo ""
    print_msg "$YELLOW" "Вам необходим GitHub Personal Access Token (PAT) с правами 'repo'."
    print_msg "$YELLOW" "Создайте его на: https://github.com/settings/tokens"
    echo ""
    read -sp "Введите ваш GitHub Personal Access Token: " github_token
    echo ""
    
    if [[ -z "$github_token" ]]; then
        print_msg "$RED" "Ошибка: Токен GitHub не может быть пустым."
        exit 1
    fi
    
    # Default clone directory
    echo ""
    read -p "Введите директорию по умолчанию для клонирования репозиториев [$HOME/mygit-repos]: " clone_dir
    clone_dir=${clone_dir:-"$HOME/mygit-repos"}
}

# Save configuration
save_config() {
    print_msg "$BLUE" "Сохранение конфигурации..."
    
    # Create config directory
    mkdir -p "$CONFIG_DIR"
    chmod 700 "$CONFIG_DIR"
    
    # Create clone directory
    mkdir -p "$clone_dir"
    
    # Save config as JSON using Python for proper escaping
    # Pass sensitive data via stdin to avoid exposure in process list
    python3 << PYTHON_SCRIPT
import json
import sys

# Read sensitive data from heredoc
github_username = "${github_username//\"/\\\"}"
github_token = """${github_token//\"/\\\"}"""
clone_dir = "${clone_dir//\"/\\\"}"
config_file = "${CONFIG_FILE//\"/\\\"}"

config = {
    'github_username': github_username,
    'github_token': github_token,
    'clone_directory': clone_dir
}

with open(config_file, 'w') as f:
    json.dump(config, f, indent=4)
PYTHON_SCRIPT
    
    # Secure the config file
    chmod 600 "$CONFIG_FILE"
    
    print_msg "$GREEN" "Конфигурация сохранена в $CONFIG_FILE"
}

# Install the main Python program
install_program() {
    print_msg "$BLUE" "Установка MyGit..."
    
    # Create installation directory
    mkdir -p "$INSTALL_DIR"
    
    # Get the directory where install.sh is located using realpath for robustness
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
    
    # Copy the Python program
    if [[ -f "$SCRIPT_DIR/mygit.py" ]]; then
        cp "$SCRIPT_DIR/mygit.py" "$INSTALL_DIR/mygit.py"
        chmod +x "$INSTALL_DIR/mygit.py"
    else
        print_msg "$RED" "Ошибка: mygit.py не найден в $SCRIPT_DIR"
        exit 1
    fi
    
    # Create symlink
    if [[ -L "$BIN_LINK" ]] || [[ -e "$BIN_LINK" ]]; then
        rm -f "$BIN_LINK"
    fi
    ln -s "$INSTALL_DIR/mygit.py" "$BIN_LINK"
    
    print_msg "$GREEN" "MyGit успешно установлен!"
    print_msg "$GREEN" "Символическая ссылка создана: $BIN_LINK"
}

# Print usage instructions
print_usage() {
    echo ""
    print_msg "$GREEN" "=============================================="
    print_msg "$GREEN" "          Установка завершена!                 "
    print_msg "$GREEN" "=============================================="
    echo ""
    print_msg "$BLUE" "Использование:"
    echo "  mygit clone <owner/repo>     - Клонировать приватный репозиторий"
    echo "  mygit run <owner/repo> <script.sh> - Клонировать и запустить скрипт"
    echo "  mygit list                   - Список клонированных репозиториев"
    echo "  mygit config                 - Показать текущую конфигурацию"
    echo "  mygit help                   - Показать справку"
    echo ""
    if [[ $EUID -ne 0 ]]; then
        print_msg "$YELLOW" "Примечание: Вам может потребоваться перезапустить терминал или выполнить:"
        print_msg "$YELLOW" "  source ~/.bashrc"
        print_msg "$YELLOW" "чтобы использовать команду 'mygit'."
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
