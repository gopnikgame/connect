# MyGit - Connect

Скрипт для подключения приватных репозиториев GitHub. 

## ⚡ Быстрая установка

```bash
wget -qO- https://raw.githubusercontent.com/gopnikgame/connect/main/install.sh | sudo bash
```

**Или с сохранением файла:**

```bash
wget -qO install.sh https://raw.githubusercontent.com/gopnikgame/connect/main/install.sh && sudo bash install.sh
```

Инструмент позволяет:
- Подключаться к приватным репозиториям GitHub
- Клонировать репозитории с аутентификацией
- Запускать shell-скрипты из клонированных репозиториев

## Требования

- Ubuntu Server (или другой дистрибутив на базе Debian)
- Git (устанавливается автоматически)
- Python 3.6+ (устанавливается автоматически)
- GitHub Personal Access Token (PAT) с правами `repo`

## Установка

### 1. Клонирование репозитория

```bash
git clone https://github.com/gopnikgame/connect.git
cd connect
```

### 2. Запуск установщика

```bash
# Для системной установки (требует sudo, автоматически установит зависимости)
sudo bash install.sh

# Для локальной установки (в домашнюю директорию)
bash install.sh
```

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
```

## Безопасность

- Конфигурационный файл `~/.mygit/config.json` защищён правами доступа 600
- Директория `~/.mygit/` защищена правами доступа 700
- Токен не отображается в логах при клонировании
- Рекомендуется использовать токены с минимально необходимыми правами

## Лицензия

MIT License - см. файл [LICENSE](LICENSE)
