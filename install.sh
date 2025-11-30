#!/usr/bin/env bash

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

# GitHub repository settings
GITHUB_REPO="gopnikgame/connect"
GITHUB_BRANCH="main"

# Installation paths
INSTALL_DIR="/opt/mygit"
CONFIG_DIR="$HOME/.mygit"
CONFIG_FILE="$CONFIG_DIR/config.json"
BIN_LINK="/usr/local/bin/mygit"

# Print colored message
print_msg() {
    local color=$1
    local msg=$2
    printf "${color}${msg}${NC}\n"
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
    if [ "$(id -u)" -ne 0 ]; then
        print_msg "$YELLOW" "Внимание: Скрипт запущен без прав root. Будет выполнена локальная установка."
        INSTALL_DIR="$HOME/.local/share/mygit"
        BIN_LINK="$HOME/.local/bin/mygit"
        mkdir -p "$HOME/.local/bin"
        # Add to PATH if not already there
        if echo ":$PATH:" | grep -q ":$HOME/.local/bin:"; then
            : # Уже в PATH
        else
            print_msg "$YELLOW" "Добавление $HOME/.local/bin в PATH в ~/.bashrc"
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
        fi
    fi
}

# Check and install dependencies
check_dependencies() {
    print_msg "$BLUE" "Проверка зависимостей..."
    
    local missing_deps=""
    local need_update=0
    
    if ! command -v git >/dev/null 2>&1; then
        missing_deps="$missing_deps git"
        need_update=1
    fi
    
    if ! command -v python3 >/dev/null 2>&1; then
        missing_deps="$missing_deps python3"
        need_update=1
    fi
    
    if ! command -v pip3 >/dev/null 2>&1; then
        missing_deps="$missing_deps python3-pip"
        need_update=1
    fi
    
    if ! command -v wget >/dev/null 2>&1 && ! command -v curl >/dev/null 2>&1; then
        missing_deps="$missing_deps wget"
        need_update=1
    fi
    
    if [ -n "$missing_deps" ]; then
        print_msg "$YELLOW" "Отсутствуют зависимости:$missing_deps"
        
        # Auto-install if running as root
        if [ "$(id -u)" -eq 0 ]; then
            print_msg "$BLUE" "Установка зависимостей..."
            
            # Update package list
            print_msg "$BLUE" "Обновление списка пакетов..."
            if ! apt-get update; then
                print_msg "$RED" "Ошибка: Не удалось обновить список пакетов."
                print_msg "$YELLOW" "Попробуйте выполнить вручную: sudo apt-get update"
                exit 1
            fi
            
            # Install missing dependencies
            print_msg "$BLUE" "Установка пакетов:$missing_deps"
            if ! apt-get install -y $missing_deps; then
                print_msg "$RED" "Ошибка: Не удалось установить зависимости."
                print_msg "$YELLOW" "Попробуйте выполнить вручную: sudo apt-get install -y$missing_deps"
                exit 1
            fi
            
            print_msg "$GREEN" "Зависимости успешно установлены."
        else
            print_msg "$YELLOW" "Пожалуйста, установите их используя:"
            print_msg "$YELLOW" "  sudo apt-get update && sudo apt-get install -y$missing_deps"
            exit 1
        fi
    else
        print_msg "$GREEN" "Все зависимости установлены."
    fi
    
    # Test internet connectivity
    print_msg "$BLUE" "Проверка подключения к GitHub..."
    if command -v wget >/dev/null 2>&1; then
        if ! wget -q --spider --timeout=10 https://raw.githubusercontent.com 2>/dev/null; then
            print_msg "$YELLOW" "Предупреждение: Нет подключения к GitHub (raw.githubusercontent.com)"
            print_msg "$YELLOW" "Это может вызвать проблемы при загрузке файлов"
        else
            print_msg "$GREEN" "Подключение к GitHub работает"
        fi
    elif command -v curl >/dev/null 2>&1; then
        if ! curl -sSf --max-time 10 https://raw.githubusercontent.com >/dev/null 2>&1; then
            print_msg "$YELLOW" "Предупреждение: Нет подключения к GitHub (raw.githubusercontent.com)"
            print_msg "$YELLOW" "Это может вызвать проблемы при загрузке файлов"
        else
            print_msg "$GREEN" "Подключение к GitHub работает"
        fi
    fi
}

get_credentials() {
    print_msg "$BLUE" "Настройка доступа к GitHub..."
    echo ""
    
    printf "Введите ваше имя пользователя GitHub: "
    read github_username
    if [ -z "$github_username" ]; then
        print_msg "$RED" "Ошибка: Имя пользователя GitHub не может быть пустым."
        exit 1
    fi
    
    echo ""
    print_msg "$YELLOW" "Вам необходим GitHub Personal Access Token (PAT) с правами 'repo'."
    print_msg "$YELLOW" "Создайте его на: https://github.com/settings/tokens"
    echo ""
    printf "Введите ваш GitHub Personal Access Token: "
    stty -echo 2>/dev/null || true
    read github_token
    stty echo 2>/dev/null || true
    echo ""
    
    if [ -z "$github_token" ]; then
        print_msg "$RED" "Ошибка: Токен GitHub не может быть пустым."
        exit 1
    fi
    
    echo ""
    printf "Введите директорию по умолчанию для клонирования репозиториев [$HOME/mygit-repos]: "
    read clone_dir
    if [ -z "$clone_dir" ]; then
        clone_dir="$HOME/mygit-repos"
    fi
}

save_config() {
    print_msg "$BLUE" "Сохранение конфигурации..."
    
    mkdir -p "$CONFIG_DIR"
    chmod 700 "$CONFIG_DIR"
    
    mkdir -p "$clone_dir"
    
    cat >> "$CONFIG_FILE" << EOF
{
    "github_username": "$github_username",
    "github_token": "$github_token",
    "clone_directory": "$clone_dir"
}
EOF
    
    chmod 600 "$CONFIG_FILE"
    
    print_msg "$GREEN" "Конфигурация сохранена в $CONFIG_FILE"
}

# Download mygit.py from GitHub
download_mygit() {
    local url="https://raw.githubusercontent.com/${GITHUB_REPO}/${GITHUB_BRANCH}/mygit.py"
    local temp_file="/tmp/mygit_$$.py"
    
    print_msg "$BLUE" "Загрузка mygit.py из GitHub..."
    print_msg "$YELLOW" "URL: $url"
    
    # Try wget first, fallback to curl
    if command -v wget >/dev/null 2>&1; then
        if wget -q -O "$temp_file" "$url" 2>/dev/null; then
            if [ -f "$temp_file" ] && [ -s "$temp_file" ]; then
                print_msg "$GREEN" "Файл успешно загружен"
                echo "$temp_file"
                return 0
            fi
        fi
    elif command -v curl >/dev/null 2>&1; then
        if curl -sSf -o "$temp_file" "$url" 2>/dev/null; then
            if [ -f "$temp_file" ] && [ -s "$temp_file" ]; then
                print_msg "$GREEN" "Файл успешно загружен"
                echo "$temp_file"
                return 0
            fi
        fi
    fi
    
    # If we got here, download failed
    rm -f "$temp_file" 2>/dev/null
    print_msg "$RED" "Ошибка: Не удалось загрузить mygit.py с GitHub."
    print_msg "$YELLOW" "Проверьте:"
    print_msg "$YELLOW" "  1. Подключение к интернету"
    print_msg "$YELLOW" "  2. Доступность GitHub"
    print_msg "$YELLOW" "  3. URL: $url"
    return 1
}

install_program() {
    print_msg "$BLUE" "Установка MyGit..."
    
    mkdir -p "$INSTALL_DIR"
    
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
    local mygit_source=""
    
    # Check if mygit.py exists locally
    if [ -f "$SCRIPT_DIR/mygit.py" ]; then
        print_msg "$GREEN" "Используется локальный файл mygit.py"
        mygit_source="$SCRIPT_DIR/mygit.py"
    else
        print_msg "$YELLOW" "Локальный файл mygit.py не найден, загрузка из GitHub..."
        mygit_source=$(download_mygit)
        
        if [ $? -ne 0 ] || [ -z "$mygit_source" ] || [ ! -f "$mygit_source" ]; then
            print_msg "$RED" "Ошибка: Не удалось загрузить mygit.py"
            exit 1
        fi
    fi
    
    # Copy to installation directory
    if [ -f "$mygit_source" ]; then
        cp "$mygit_source" "$INSTALL_DIR/mygit.py"
        chmod +x "$INSTALL_DIR/mygit.py"
        
        # Clean up temp file if it was downloaded
        if echo "$mygit_source" | grep -q "^/tmp/mygit_"; then
            rm -f "$mygit_source"
        fi
    else
        print_msg "$RED" "Ошибка: Не удалось найти mygit.py"
        exit 1
    fi
    
    # Create symbolic link
    if [ -L "$BIN_LINK" ] || [ -e "$BIN_LINK" ]; then
        rm -f "$BIN_LINK"
    fi
    ln -s "$INSTALL_DIR/mygit.py" "$BIN_LINK"
    
    print_msg "$GREEN" "MyGit успешно установлен!"
    print_msg "$GREEN" "Символическая ссылка создана: $BIN_LINK"
}

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
    echo "  mygit --help                 - Показать справку"
    echo ""
    if [ "$(id -u)" -ne 0 ]; then
        print_msg "$YELLOW" "Примечание: Вам может потребоваться перезапустить терминал или выполнить:"
        print_msg "$YELLOW" "  source ~/.bashrc"
        print_msg "$YELLOW" "чтобы использовать команду 'mygit'."
    fi
}

main() {
    print_header
    check_permissions
    check_dependencies
    get_credentials
    save_config
    install_program
    print_usage
}

main