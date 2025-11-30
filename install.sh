#!/usr/bin/env bash

# =============================================================================
# MyGit Installer Script
# Скрипт установки коннектора приватных репозиториев
# Разработан для операционных систем Ubuntu server
# ==============================================================================

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
    
    # Overwrite config file (not append)
    cat > "$CONFIG_FILE" << EOF
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
    local url="https://raw.githubusercontent.com/${GITHUB_REPO}/refs/heads/${GITHUB_BRANCH}/mygit.py"
    local temp_file="/tmp/mygit_$$.py"
    
    # All output to stderr
    {
        print_msg "$BLUE" "Загрузка mygit.py из GitHub..."
        print_msg "$YELLOW" "URL: $url"
    } >&2
    
    # Remove any existing temp file
    rm -f "$temp_file" 2>/dev/null
    
    # Try wget first
    if command -v wget >/dev/null 2>&1; then
        print_msg "$BLUE" "Используется wget для загрузки..." >&2
        
        # Download with verbose output redirected
        if wget -q -O "$temp_file" "$url"; then
            # Check if file exists and has content
            if [ -f "$temp_file" ] && [ -s "$temp_file" ]; then
                # Verify it's a Python script (check shebang)
                local first_line=$(head -n 1 "$temp_file")
                if echo "$first_line" | grep -q "python"; then
                    local file_size=$(stat -f%z "$temp_file" 2>/dev/null || stat -c%s "$temp_file" 2>/dev/null)
                    print_msg "$GREEN" "Файл успешно загружен ($file_size байт)" >&2
                    # Only output the file path to stdout
                    echo "$temp_file"
                    return 0
                else
                    print_msg "$YELLOW" "Предупреждение: Загружен не Python файл" >&2
                    print_msg "$YELLOW" "Первая строка: $first_line" >&2
                fi
            else
                print_msg "$YELLOW" "Файл пустой или не создан" >&2
            fi
        else
            print_msg "$YELLOW" "wget вернул ошибку: $?" >&2
        fi
    fi
    
    # Try curl as fallback
    if command -v curl >/dev/null 2>&1; then
        print_msg "$BLUE" "Используется curl для загрузки..." >&2
        
        # Download with curl
        if curl -sSL -o "$temp_file" "$url"; then
            # Check if file exists and has content
            if [ -f "$temp_file" ] && [ -s "$temp_file" ]; then
                # Verify it's a Python script
                local first_line=$(head -n 1 "$temp_file")
                if echo "$first_line" | grep -q "python"; then
                    local file_size=$(stat -f%z "$temp_file" 2>/dev/null || stat -c%s "$temp_file" 2>/dev/null)
                    print_msg "$GREEN" "Файл успешно загружен ($file_size байт)" >&2
                    # Only output the file path to stdout
                    echo "$temp_file"
                    return 0
                else
                    print_msg "$YELLOW" "Предупреждение: Загружен не Python файл" >&2
                    print_msg "$YELLOW" "Первая строка: $first_line" >&2
                fi
            else
                print_msg "$YELLOW" "Файл пустой или не создан" >&2
            fi
        else
            print_msg "$YELLOW" "curl вернул ошибку: $?" >&2
        fi
    fi
    
    # If we got here, download failed
    rm -f "$temp_file" 2>/dev/null
    {
        print_msg "$RED" "Ошибка: Не удалось загрузить mygit.py с GitHub."
        print_msg "$YELLOW" ""
        print_msg "$YELLOW" "Возможные причины:"
        print_msg "$YELLOW" "  1. Нет подключения к интернету"
        print_msg "$YELLOW" "  2. GitHub недоступен"
        print_msg "$YELLOW" "  3. Файл не существует в репозитории"
        print_msg "$YELLOW" ""
        print_msg "$YELLOW" "Диагностика:"
        print_msg "$YELLOW" "  Попробуйте вручную: curl -I $url"
    } >&2
    
    return 1
}

install_program() {
    print_msg "$BLUE" "Установка MyGit..."
    
    mkdir -p "$INSTALL_DIR"
    
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd -P)"
    local mygit_source=""
    local download_status=0
    
    # Check if mygit.py exists locally
    if [ -f "$SCRIPT_DIR/mygit.py" ]; then
        print_msg "$GREEN" "Используется локальный файл mygit.py"
        mygit_source="$SCRIPT_DIR/mygit.py"
    else
        print_msg "$YELLOW" "Локальный файл mygit.py не найден, загрузка из GitHub..."
        
        # Call download function and capture both output and return code
        mygit_source=$(download_mygit)
        download_status=$?
        
        # Debug output
        print_msg "$BLUE" "Debug: download_status=$download_status" >&2
        print_msg "$BLUE" "Debug: mygit_source='$mygit_source'" >&2
        
        # Check if download was successful
        if [ $download_status -ne 0 ]; then
            print_msg "$RED" "Ошибка: Не удалось загрузить mygit.py (код: $download_status)"
            print_msg "$YELLOW" ""
            print_msg "$YELLOW" "Альтернативные способы установки:"
            print_msg "$YELLOW" "  1. Клонируйте репозиторий полностью:"
            print_msg "$YELLOW" "     git clone https://github.com/${GITHUB_REPO}.git"
            print_msg "$YELLOW" "     cd connect && sudo bash install.sh"
            print_msg "$YELLOW" ""
            print_msg "$YELLOW" "  2. Скачайте файл вручную:"
            print_msg "$YELLOW" "     wget https://raw.githubusercontent.com/${GITHUB_REPO}/refs/heads/${GITHUB_BRANCH}/mygit.py"
            print_msg "$YELLOW" "     sudo bash install.sh"
            exit 1
        fi
        
        # Verify the downloaded file path
        if [ -z "$mygit_source" ]; then
            print_msg "$RED" "Ошибка: Путь к файлу пустой"
            exit 1
        fi
        
        if [ ! -f "$mygit_source" ]; then
            print_msg "$RED" "Ошибка: Файл не существует: $mygit_source"
            exit 1
        fi
        
        if [ ! -s "$mygit_source" ]; then
            print_msg "$RED" "Ошибка: Файл пустой: $mygit_source"
            exit 1
        fi
        
        print_msg "$GREEN" "Файл найден: $mygit_source ($(wc -c < "$mygit_source") байт)"
    fi
    
    # Verify it's a Python file
    if ! head -n 1 "$mygit_source" | grep -q "python"; then
        print_msg "$RED" "Ошибка: Файл не является Python скриптом"
        print_msg "$YELLOW" "Первая строка: $(head -n 1 "$mygit_source")"
        exit 1
    fi
    
    # Copy to installation directory
    print_msg "$BLUE" "Копирование $mygit_source в $INSTALL_DIR..."
    if ! cp "$mygit_source" "$INSTALL_DIR/mygit.py"; then
        print_msg "$RED" "Ошибка: Не удалось скопировать файл"
        exit 1
    fi
    
    chmod +x "$INSTALL_DIR/mygit.py"
    
    # Clean up temp file if it was downloaded
    if echo "$mygit_source" | grep -q "^/tmp/mygit_"; then
        print_msg "$BLUE" "Очистка временных файлов..."
        rm -f "$mygit_source"
    fi
    
    # Create symbolic link
    if [ -L "$BIN_LINK" ] || [ -e "$BIN_LINK" ]; then
        rm -f "$BIN_LINK"
    fi
    
    if ! ln -s "$INSTALL_DIR/mygit.py" "$BIN_LINK"; then
        print_msg "$RED" "Ошибка: Не удалось создать символическую ссылку"
        exit 1
    fi
    
    print_msg "$GREEN" "MyGit успешно установлен!"
    print_msg "$GREEN" "Файл программы: $INSTALL_DIR/mygit.py"
    print_msg "$GREEN" "Символическая ссылка: $BIN_LINK"
    print_msg "$GREEN" "Конфигурация: $CONFIG_FILE"
    
    # Verify installation
    if [ -x "$BIN_LINK" ]; then
        print_msg "$GREEN" "Проверка установки: OK"
    else
        print_msg "$YELLOW" "Предупреждение: Файл установлен, но может быть недоступен"
    fi
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