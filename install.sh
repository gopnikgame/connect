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
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# GitHub repository settings
GITHUB_REPO="gopnikgame/connect"
GITHUB_BRANCH="main"

# Installation paths
INSTALL_DIR="/opt/mygit"
CONFIG_DIR="$HOME/.mygit"
CONFIG_FILE="$CONFIG_DIR/config.json"
BIN_LINK="/usr/local/bin/mygit"

# Installation mode flag
UPDATE_MODE=false

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
    if [ "$UPDATE_MODE" = true ]; then
        print_msg "$BLUE" "   MyGit - Обновление программы             "
    else
        print_msg "$CYAN" "   MyGit - Коннектор приватных репозиториев   "
        print_msg "$CYAN" "   Интерактивный режим + GitHub API          "
    fi
    print_msg "$BLUE" "=============================================="
    echo ""
}

# Check if config exists
check_existing_config() {
    if [ -f "$CONFIG_FILE" ]; then
        print_msg "$GREEN" "Обнаружена существующая конфигурация: $CONFIG_FILE"
        print_msg "$YELLOW" "Режим обновления: конфигурация будет сохранена, обновится только программа."
        UPDATE_MODE=true
        return 0
    else
        print_msg "$BLUE" "Конфигурация не найдена. Выполняется первичная установка."
        UPDATE_MODE=false
        return 1
    fi
}

# Check if running as root for system-wide installation
check_permissions() {
    if [ "$(id -u)" -ne 0 ]; then
        print_msg "$YELLOW" "Внимание: Скрипт запущен без прав root. Будет выполнена локальная установка."
        INSTALL_DIR="$HOME/.local/share/mygit"
        BIN_LINK="$HOME/.local/bin/mygit"
        
        # Update CONFIG_FILE path check after INSTALL_DIR is set
        if [ "$UPDATE_MODE" = false ]; then
            CONFIG_DIR="$HOME/.mygit"
            CONFIG_FILE="$CONFIG_DIR/config.json"
        fi
        
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
    
    # Check Python version
    print_msg "$BLUE" "Проверка версии Python..."
    python_version=$(python3 --version 2>&1 | awk '{print $2}')
    python_major=$(echo "$python_version" | cut -d. -f1)
    python_minor=$(echo "$python_version" | cut -d. -f2)
    
    if [ "$python_major" -lt 3 ] || ([ "$python_major" -eq 3 ] && [ "$python_minor" -lt 6 ]); then
        print_msg "$RED" "Ошибка: Требуется Python 3.6 или выше (обнаружен $python_version)"
        exit 1
    fi
    print_msg "$GREEN" "Python версия: $python_version ✓"
    
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
    
    # Test GitHub API connectivity
    print_msg "$BLUE" "Проверка подключения к GitHub API..."
    if command -v curl >/dev/null 2>&1; then
        if curl -sSf --max-time 10 https://api.github.com >/dev/null 2>&1; then
            print_msg "$GREEN" "Подключение к GitHub API работает"
        else
            print_msg "$YELLOW" "Предупреждение: GitHub API может быть недоступен"
        fi
    fi
}

# Validate GitHub token
validate_github_token() {
    local username=$1
    local token=$2
    
    print_msg "$BLUE" "Проверка токена GitHub..."
    
    if ! command -v curl >/dev/null 2>&1; then
        print_msg "$YELLOW" "Предупреждение: curl не установлен, пропуск проверки токена"
        return 0
    fi
    
    # Test API access
    local response=$(curl -s -H "Authorization: token $token" \
                          -H "Accept: application/vnd.github.v3+json" \
                          -w "\n%{http_code}" \
                          https://api.github.com/user 2>/dev/null)
    
    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        local api_username=$(echo "$body" | grep -o '"login"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4)
        
        if [ -n "$api_username" ]; then
            if [ "$api_username" != "$username" ]; then
                print_msg "$YELLOW" "Предупреждение: Токен принадлежит пользователю '$api_username', а не '$username'"
                print_msg "$YELLOW" "Продолжить? [y/N]: "
                read -r confirm
                if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
                    print_msg "$RED" "Установка отменена"
                    exit 1
                fi
            else
                print_msg "$GREEN" "Токен успешно проверен для пользователя: $api_username ✓"
            fi
            
            # Check token scopes
            local scopes_header=$(curl -s -I \
                                      -H "Authorization: token $token" \
                                      https://api.github.com/user 2>/dev/null | \
                                      grep -i "x-oauth-scopes:" | cut -d: -f2 | tr -d '[:space:]')
            
            if echo "$scopes_header" | grep -q "repo"; then
                print_msg "$GREEN" "Токен имеет необходимые права доступа (repo) ✓"
            else
                print_msg "$YELLOW" "Предупреждение: Токен может не иметь прав 'repo'"
                print_msg "$YELLOW" "Текущие права: $scopes_header"
                print_msg "$YELLOW" "Для доступа к приватным репозиториям требуется право 'repo'"
            fi
        fi
    elif [ "$http_code" = "401" ]; then
        print_msg "$RED" "Ошибка: Неверный токен доступа"
        print_msg "$YELLOW" "Проверьте токен на: https://github.com/settings/tokens"
        exit 1
    elif [ "$http_code" = "403" ]; then
        print_msg "$RED" "Ошибка: Доступ запрещен (возможно, токен истек)"
        exit 1
    else
        print_msg "$YELLOW" "Предупреждение: Не удалось проверить токен (HTTP $http_code)"
        print_msg "$YELLOW" "Продолжить установку? [y/N]: "
        read -r confirm
        if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
            print_msg "$RED" "Установка отменена"
            exit 1
        fi
    fi
}

get_credentials() {
    print_msg "$CYAN" "=============================================="
    print_msg "$CYAN" "   Настройка доступа к GitHub                 "
    print_msg "$CYAN" "=============================================="
    echo ""
    
    printf "Введите ваше имя пользователя GitHub: "
    read github_username
    if [ -z "$github_username" ]; then
        print_msg "$RED" "Ошибка: Имя пользователя GitHub не может быть пустым."
        exit 1
    fi
    
    echo ""
    print_msg "$YELLOW" "Вам необходим GitHub Personal Access Token (PAT)."
    print_msg "$YELLOW" ""
    print_msg "$YELLOW" "Требуемые права (scopes):"
    print_msg "$YELLOW" "  ✓ repo - полный доступ к репозиториям (обязательно)"
    print_msg "$YELLOW" "  ✓ read:org - чтение информации об организациях (рекомендуется)"
    print_msg "$YELLOW" ""
    print_msg "$CYAN" "Создайте токен здесь: https://github.com/settings/tokens"
    print_msg "$CYAN" "Или используйте новый тип токена: https://github.com/settings/personal-access-tokens/new"
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
    
    # Validate the token
    validate_github_token "$github_username" "$github_token"
    
    echo ""
    printf "Введите директорию по умолчанию для клонирования репозиториев [$HOME/mygit-repos]: "
    read clone_dir
    if [ -z "$clone_dir" ]; then
        clone_dir="$HOME/mygit-repos"
    fi
    
    # Expand tilde if present
    clone_dir="${clone_dir/#\~/$HOME}"
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
    print_msg "$GREEN" "Директория клонирования: $clone_dir"
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
    
    # Create wrapper script instead of symbolic link
    if [ -e "$BIN_LINK" ]; then
        rm -f "$BIN_LINK"
    fi
    
    print_msg "$BLUE" "Создание wrapper скрипта..."
    cat > "$BIN_LINK" << 'EOF'
#!/usr/bin/env bash
exec python3 "INSTALL_DIR_PLACEHOLDER/mygit.py" "$@"
EOF
    
    # Replace placeholder with actual install directory
    sed -i "s|INSTALL_DIR_PLACEHOLDER|$INSTALL_DIR|g" "$BIN_LINK"
    
    chmod +x "$BIN_LINK"
    
    print_msg "$GREEN" "MyGit успешно установлен!"
    print_msg "$GREEN" "Файл программы: $INSTALL_DIR/mygit.py"
    print_msg "$GREEN" "Wrapper скрипт: $BIN_LINK"
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
    if [ "$UPDATE_MODE" = true ]; then
        print_msg "$GREEN" "=============================================="
        print_msg "$GREEN" "          Обновление завершено!                "
        print_msg "$GREEN" "=============================================="
        echo ""
        print_msg "$BLUE" "Программа обновлена. Конфигурация сохранена."
    else
        print_msg "$GREEN" "=============================================="
        print_msg "$GREEN" "          Установка завершена!                 "
        print_msg "$GREEN" "=============================================="
    fi
    echo ""
    print_msg "$CYAN" "🚀 Основные возможности MyGit:"
    echo ""
    print_msg "$BLUE" "📋 ИНТЕРАКТИВНЫЙ РЕЖИМ (рекомендуется):"
    echo "  mygit                        - Запустить интерактивное меню"
    echo "                                 • Просмотр всех ваших репозиториев на GitHub"
    echo "                                 • Клонирование через меню"
    echo "                                 • Автопоиск .sh скриптов"
    echo "                                 • Запуск скриптов через GUI"
    echo ""
    print_msg "$BLUE" "⚡ КОМАНДНАЯ СТРОКА (для автоматизации):"
    echo "  mygit clone <owner/repo>     - Клонировать приватный репозиторий"
    echo "  mygit pull <owner/repo>      - Обновить репозиторий"
    echo "  mygit run <owner/repo> <script.sh> - Клонировать и запустить скрипт"
    echo "  mygit list                   - Список клонированных репозиториев"
    echo "  mygit config                 - Показать текущую конфигурацию"
    echo "  mygit --help                 - Показать справку"
    echo ""
    print_msg "$CYAN" "💡 Совет: Запустите просто 'mygit' для интерактивной работы!"
    echo ""
    
    if [ "$(id -u)" -ne 0 ]; then
        print_msg "$YELLOW" "⚠️  Примечание: Вам может потребоваться перезапустить терминал или выполнить:"
        print_msg "$YELLOW" "  source ~/.bashrc"
        print_msg "$YELLOW" "чтобы использовать команду 'mygit'."
        echo ""
    fi
    
    print_msg "$GREEN" "✅ Готово к использованию! Запустите: mygit"
}

main() {
    ## Check for existing config first
    check_existing_config
    
    print_header
    check_permissions
    check_dependencies
    
    # Only ask for credentials if config doesn't exist
    if [ "$UPDATE_MODE" = false ]; then
        get_credentials
        save_config
    else
        print_msg "$BLUE" "Пропуск настройки конфигурации (уже существует)."
    fi
    
    install_program
    print_usage
}

main