# MyGit - Connect

Скрипт для подключения приватных репозиториев GitHub. 

## ⚡ Быстрая установка (одна команда)

```bash
wget -qO- https://raw.githubusercontent.com/gopnikgame/connect/main/install.sh | sudo bash
```

**Или с сохранением файла установщика:**

```bash
wget -qO install.sh https://raw.githubusercontent.com/gopnikgame/connect/main/install.sh && sudo bash install.sh
```

> **Примечание:** Скрипт автоматически загрузит `mygit.py` из GitHub и установит все необходимые зависимости.

Инструмент позволяет:
- Подключаться к приватным репозиториям GitHub
- Клонировать репозитории с аутентификацией
- Запускать shell-скрипты из клонированных репозиториев

## Требования

- Ubuntu Server (или другой дистрибутив на базе Debian)
- Права root для системной установки (необязательно)

**Зависимости (устанавливаются автоматически):**
- Git
- Python 3.6+
- wget или curl

## Установка

### Вариант 1: Быстрая установка (рекомендуется)

Скачивает и устанавливает одной командой, автоматически загружая все файлы из GitHub:

```bash
# С правами root (системная установка)
wget -qO- https://raw.githubusercontent.com/gopnikgame/connect/main/install.sh | sudo bash

# Без root (локальная установка в ~/.local)
wget -qO- https://raw.githubusercontent.com/gopnikgame/connect/main/install.sh | bash
```

### Вариант 2: Клонирование репозитория

Для разработки или ручной установки:

```bash
# 1. Клонирование репозитория
git clone https://github.com/gopnikgame/connect.git
cd connect

# 2. Запуск установщика
# Для системной установки (автоматически установит зависимости)
sudo bash install.sh

# Для локальной установки (в домашнюю директорию)
bash install.sh
```

### Что происходит при установке?

1. **Проверка прав** - определяет режим установки (системная/локальная)
2. **Установка зависимостей** - автоматически устанавливает git, python3, wget (если нужно)
3. **Загрузка mygit.py** - скачивает основной скрипт из GitHub (если не найден локально)
4. **Настройка доступа** - запрашивает GitHub credentials
5. **Создание конфигурации** - сохраняет настройки в `~/.mygit/config.json`
6. **Установка программы** - копирует файлы и создает символическую ссылку

При установке будет запрошено:
- **GitHub username** - ваше имя пользователя на GitHub
- **GitHub Personal Access Token** - токен доступа с правами `repo`
- **Clone directory** - директория для клонирования репозиториев (по умолчанию `~/mygit-repos`)

### Создание Personal Access Token

1. Перейдите на https://github.com/settings/tokens
2. Нажмите "Generate new token" → "Generate new token (classic)"
3. Выберите scope `repo` (Full control of private repositories)
4. Скопируйте сгенерированный токен

## Использование

После установки команда `mygit` будет доступна в терминале.

### Клонирование репозитория

```bash
# Клонировать приватный репозиторий
mygit clone owner/repository

# Принудительно переклонировать (удалить существующий и клонировать заново)
mygit clone owner/repository --force
```

### Обновление репозитория

```bash
mygit pull owner/repository
```

### Запуск скрипта из репозитория

```bash
# Клонирует (если нужно) и запускает скрипт
mygit run owner/repository script.sh

# С аргументами для скрипта
mygit run owner/repository scripts/deploy.sh --env production

# Без подтверждения (автоматический запуск)
mygit run owner/repository script.sh --yes
```

### Список клонированных репозиториев

```bash
mygit list
```

### Просмотр конфигурации

```bash
mygit config
```

### Справка

```bash
mygit --help
mygit clone --help
```

## Структура файлов

```
~/.mygit/
└── config.json     # Конфигурация (username, token, clone_directory)

~/mygit-repos/      # Директория для клонированных репозиториев (по умолчанию)
├── repo1/
├── repo2/
└── ...

# Системная установка
/opt/mygit/
└── mygit.py        # Основной скрипт

/usr/local/bin/
└── mygit           # Символическая ссылка

# Локальная установка (без sudo)
~/.local/share/mygit/
└── mygit.py        # Основной скрипт

~/.local/bin/
└── mygit           # Символическая ссылка
```

## Переустановка или обновление

Просто запустите установщик заново:

```bash
wget -qO- https://raw.githubusercontent.com/gopnikgame/connect/main/install.sh | sudo bash
```

Существующая конфигурация (`~/.mygit/config.json`) будет перезаписана.

## Удаление

```bash
# Системная установка
sudo rm -rf /opt/mygit
sudo rm -f /usr/local/bin/mygit
rm -rf ~/.mygit

# Локальная установка
rm -rf ~/.local/share/mygit
rm -f ~/.local/bin/mygit
rm -rf ~/.mygit
```

## Безопасность

- Конфигурационный файл `~/.mygit/config.json` защищён правами доступа 600
- Директория `~/.mygit/` защищена правами доступа 700
- Токен не отображается в логах при клонировании
- После клонирования учетные данные удаляются из `.git/config`
- Рекомендуется использовать токены с минимально необходимыми правами

## Устранение неполадок

### Ошибка: command not found после установки

Если после локальной установки команда `mygit` не найдена:

```bash
# Перезагрузите конфигурацию bash
source ~/.bashrc

# Или добавьте PATH вручную
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Ошибка: Permission denied

Если не хватает прав для системной установки:

```bash
# Используйте локальную установку без sudo
wget -qO- https://raw.githubusercontent.com/gopnikgame/connect/main/install.sh | bash
```

## Лицензия

MIT License - см. файл [LICENSE](LICENSE)
