#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MyGit - Коннектор приватных репозиториев GitHub

Инструмент для подключения к приватным репозиториям GitHub,
их клонирования и запуска shell-скриптов.

Разработан для операционных систем Ubuntu server.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
import urllib.request
import urllib.error


class TerminalUI:
    """Единое оформление интерактивного терминального интерфейса."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    MAGENTA = "\033[35m"
    WHITE = "\033[97m"
    WIDTH = 64

    def __init__(self):
        self.color_enabled = (
            sys.stdout.isatty()
            and "NO_COLOR" not in os.environ
            and os.environ.get("TERM") != "dumb"
        )
        if self.color_enabled and os.name == "nt":
            os.system("")

    def style(self, text, *codes):
        if not self.color_enabled or not codes:
            return str(text)
        return f"{''.join(codes)}{text}{self.RESET}"

    def header(self, title, subtitle=None):
        line = "─" * self.WIDTH
        print(self.style(f"┌{line}┐", self.CYAN))
        print(self.style(f"  {title}", self.BOLD, self.WHITE))
        if subtitle:
            print(self.style(f"  {subtitle}", self.DIM))
        print(self.style(f"└{line}┘", self.CYAN))

    def section(self, title):
        print(self.style(f"\n  {title}", self.BOLD, self.CYAN))
        print(self.style("  " + "─" * (self.WIDTH - 2), self.DIM))

    def option(self, key, title, hint=None, color=None):
        key_text = self.style(f"[{key}]", self.BOLD, color or self.GREEN)
        print(f"  {key_text} {self.style(title, self.BOLD)}")
        if hint:
            print(self.style(f"      {hint}", self.DIM))

    def prompt(self, text):
        return self.style(f"\n  › {text} ", self.BOLD, self.YELLOW)

    def status(self, kind, message):
        styles = {
            "success": ("✓", self.GREEN),
            "warning": ("!", self.YELLOW),
            "error": ("×", self.RED),
            "info": ("•", self.CYAN),
        }
        marker, color = styles[kind]
        print(f"\n  {self.style(marker, self.BOLD, color)} {message}")


class Config:
    """Менеджер конфигурации для MyGit."""
    
    def __init__(self):
        self.config_dir = Path.home() / ".mygit"
        self.config_file = self.config_dir / "config.json"
        self._config = None
    
    def load(self):
        """Загрузить конфигурацию из файла."""
        if not self.config_file.exists():
            print("Ошибка: Конфигурация не найдена.")
            print("Пожалуйста, сначала запустите установщик: ./install.sh")
            sys.exit(1)
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Ошибка: Некорректный файл конфигурации: {e}")
            sys.exit(1)
        except IOError as e:
            print(f"Ошибка: Невозможно прочитать файл конфигурации: {e}")
            sys.exit(1)
        
        return self._config
    
    @property
    def username(self):
        """Получить имя пользователя GitHub."""
        if self._config is None:
            self.load()
        return self._config.get("github_username", "")
    
    @property
    def token(self):
        """Получить персональный токен доступа GitHub."""
        if self._config is None:
            self.load()
        return self._config.get("github_token", "")
    
    @property
    def clone_directory(self):
        """Получить директорию клонирования по умолчанию."""
        if self._config is None:
            self.load()
        return Path(self._config.get("clone_directory", str(Path.home() / "mygit-repos")))
    
    def show(self):
        """Отобразить текущую конфигурацию (скрывая чувствительные данные)."""
        if self._config is None:
            self.load()
        
        print("\nТекущая конфигурация:")
        print("-" * 40)
        print(f"Имя пользователя GitHub: {self.username}")
        print(f"Токен GitHub: {'*' * 16} (настроен)")
        print(f"Директория клонирования: {self.clone_directory}")
        print("-" * 40)


class GitHubAPI:
    """Класс для работы с GitHub API."""
    
    def __init__(self, username, token):
        self.username = username
        self.token = token
        self.api_base = "https://api.github.com"
    
    def _make_request(self, endpoint):
        """Выполнить запрос к GitHub API."""
        url = f"{self.api_base}{endpoint}"
        request = urllib.request.Request(url)
        request.add_header("Authorization", f"token {self.token}")
        request.add_header("Accept", "application/vnd.github.v3+json")
        
        try:
            with urllib.request.urlopen(request) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 401:
                print("Ошибка: Неверный токен доступа")
            elif e.code == 403:
                print("Ошибка: Доступ запрещен. Проверьте права токена")
            else:
                print(f"Ошибка HTTP {e.code}: {e.reason}")
            return None
        except urllib.error.URLError as e:
            print(f"Ошибка соединения: {e.reason}")
            return None
    
    def get_user_repos(self):
        """Получить список всех репозиториев пользователя."""
        repos = []
        page = 1
        per_page = 100
        
        while True:
            endpoint = f"/user/repos?page={page}&per_page={per_page}&affiliation=owner,collaborator"
            data = self._make_request(endpoint)
            
            if data is None:
                break
            
            if not data:
                break
            
            repos.extend(data)
            
            if len(data) < per_page:
                break
            
            page += 1
        
        return repos


class GitHubRepo:
    """Менеджер операций с репозиториями GitHub."""
    
    def __init__(self, config):
        self.config = config
        self.api = GitHubAPI(config.username, config.token)
    
    def _build_clone_url(self, repo_path):
        """Построить URL клонирования для репозитория (без учетных данных)."""
        return f"https://github.com/{repo_path}.git"
    
    def _get_repo_dir(self, repo_path):
        """Получить локальный путь к директории репозитория."""
        repo_name = repo_path.split("/")[-1]
        return self.config.clone_directory / repo_name
    
    def clone(self, repo_path, force=False):
        """
        Клонировать приватный репозиторий.
        
        Args:
            repo_path: Путь к репозиторию в формате 'owner/repo'
            force: Если True, удалить существующую директорию и переклонировать
        
        Returns:
            Путь к клонированному репозиторию или None при ошибке
        """
        if "/" not in repo_path:
            print("Ошибка: Некорректный формат репозитория. Используйте 'owner/repo'")
            return None
        
        repo_dir = self._get_repo_dir(repo_path)
        
        # Check if already cloned
        if repo_dir.exists():
            if force:
                print(f"Удаление существующей директории: {repo_dir}")
                try:
                    shutil.rmtree(repo_dir)
                except OSError as e:
                    print(f"Ошибка удаления директории: {e}")
                    return None
            else:
                print(f"\n⚠️  Репозиторий уже существует по адресу: {repo_dir}")
                print("\nВыберите действие:")
                print("  1. Оставить как есть (по умолчанию)")
                print("  2. Удалить и переклонировать заново")
                print("  3. Обновить через git pull")
                
                try:
                    choice = input("\nВаш выбор [1/2/3]: ").strip()
                except (EOFError, KeyboardInterrupt):
                    choice = '1'
                
                if choice == '2':
                    print(f"\nУдаление существующей директории: {repo_dir}")
                    try:
                        shutil.rmtree(repo_dir)
                        print("Директория удалена. Переклонирование...")
                        # Continue to cloning below
                    except OSError as e:
                        print(f"Ошибка удаления директории: {e}")
                        return None
                elif choice == '3':
                    print(f"\nОбновление репозитория...")
                    if self.pull(repo_path):
                        print("Репозиторий успешно обновлен!")
                        return repo_dir
                    else:
                        print("\nОшибка обновления. Попробуйте переклонировать (выбор 2).")
                        return None
                else:
                    print(f"\nИспользуется существующий репозиторий: {repo_dir}")
                    return repo_dir
        
        # Ensure parent directory exists
        self.config.clone_directory.mkdir(parents=True, exist_ok=True)
        
        # Build authenticated URL for cloning
        clone_url = f"https://{self.config.username}:{self.config.token}@github.com/{repo_path}.git"
        print(f"Клонирование {repo_path}...")
        
        try:
            # User subprocess with capture_output to prevent credentials from appearing in output
            result = subprocess.run(
                ["git", "clone", clone_url, str(repo_dir)],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                # Sanitize error message to remove credentials
                error_msg = result.stderr.replace(self.config.token, "***")
                error_msg = error_msg.replace(self.config.username, "***")
                print(f"Ошибка клонирования репозитория: {error_msg}")
                return None
            
            # Remove credentials from remote URL after cloning
            self._sanitize_remote_url(repo_dir, repo_path)
            
            print(f"✅ Успешно клонировано в: {repo_dir}")
            return repo_dir
            
        except subprocess.SubprocessError as e:
            print(f"Ошибка: Не удалось выполнить команду git: {e}")
            return None
    
    def _sanitize_remote_url(self, repo_dir, repo_path):
        """Удалить учетные данные из URL удаленного репозитория в .git/config."""
        try:
            clean_url = f"https://github.com/{repo_path}.git"
            subprocess.run(
                ["git", "remote", "set-url", "origin", clean_url],
                cwd=str(repo_dir),
                capture_output=True,
                check=True
            )
        except subprocess.SubprocessError:
            # Non-critical error, continue silently
            pass
    
    def pull(self, repo_path):
        """
        Получить последние изменения для репозитория.
        
        Args:
            repo_path: Путь к репозиторию в формате 'owner/repo'
        
        Returns:
            True при успехе, False при ошибке
        """
        repo_dir = self._get_repo_dir(repo_path)
        
        if not repo_dir.exists():
            print(f"Ошибка: Репозиторий не найден по адресу {repo_dir}")
            print(f"Сначала клонируйте его с помощью: mygit clone {repo_path}")
            return False
        
        print(f"Получение последних изменений для {repo_path}...")
        
        # Temporarily set remote URL with credentials for pull
        auth_url = f"https://{self.config.username}:{self.config.token}@github.com/{repo_path}.git"
        clean_url = f"https://github.com/{repo_path}.git"
        
        try:
            # Set authenticated URL
            subprocess.run(
                ["git", "remote", "set-url", "origin", auth_url],
                cwd=str(repo_dir),
                capture_output=True,
                check=True
            )
            
            # Perform pull
            result = subprocess.run(
                ["git", "pull"],
                cwd=str(repo_dir),
                capture_output=True,
                text=True
            )
            
            # Always restore clean URL (even if pull failed)
            subprocess.run(
                ["git", "remote", "set-url", "origin", clean_url],
                cwd=str(repo_dir),
                capture_output=True,
                check=False
            )
            
            if result.returncode != 0:
                # Sanitize error message to remove credentials
                error_msg = result.stderr.replace(self.config.token, "***")
                error_msg = error_msg.replace(self.config.username, "***")
                print(f"Ошибка получения изменений репозитория: {error_msg}")
                return False
            
            print(result.stdout)
            return True
            
        except subprocess.SubprocessError as e:
            # Restore clean URL in case of exception
            try:
                subprocess.run(
                    ["git", "remote", "set-url", "origin", clean_url],
                    cwd=str(repo_dir),
                    capture_output=True,
                    check=False
                )
            except:
                pass
            
            print(f"Ошибка: Не удалось выполнить команду git: {e}")
            return False
    
    def run_script(self, repo_path, script_path, args=None, no_confirm=False):
        """
        Клонировать (если необходимо) и запустить shell-скрипт из репозитория.
        
        Args:
            repo_path: Путь к репозиторию в формате 'owner/repo'
            script_path: Путь к скрипту в репозитории
            args: Дополнительные аргументы для передачи скрипту
            no_confirm: Пропустить запрос подтверждения
        
        Returns:
            Код выхода скрипта
        """
        # Clone if not already present
        repo_dir = self._get_repo_dir(repo_path)
        if not repo_dir.exists():
            repo_dir = self.clone(repo_path)
            if repo_dir is None:
                return 1
        
        # Construct full script path
        full_script_path = repo_dir / script_path
        
        if not full_script_path.exists():
            print(f"Ошибка: Скрипт не найден: {full_script_path}")
            return 1
        
        if not full_script_path.is_file():
            print(f"Ошибка: Не является файлом: {full_script_path}")
            return 1
        
        # Security check: validate script path is within repository (prevent path traversal)
        try:
            full_script_path = full_script_path.resolve()
            repo_dir_resolved = repo_dir.resolve()
            if not str(full_script_path).startswith(str(repo_dir_resolved)):
                print("Ошибка: Обнаружен обход пути скрипта. Операция отменена.")
                return 1
        except (OSError, ValueError) as e:
            print(f"Ошибка: Некорректный путь к скрипту: {e}")
            return 1
        
        # Require user confirmation before making file executable and running
        if not no_confirm:
            print(f"\nСкрипт для выполнения: {full_script_path}")
            print(f"Репозиторий: {repo_path}")
            try:
                confirm = input("\nВы уверены, что хотите запустить этот скрипт? [y/N]: ").strip().lower()
            except EOFError:
                confirm = 'n'
            if confirm != 'y':
                print("Операция отменена.")
                return 0
        
        # Make script executable (optional, since we'll use bash explicitly)
        try:
            os.chmod(full_script_path, 0o755)
        except OSError:
            pass
        
        # Run the script using bash explicitly
        print(f"\nЗапуск скрипта: {script_path}")
        print("-" * 40)
        
        # Use bash to execute the script to handle missing shebang and line ending issues
        cmd = ["bash", str(full_script_path)]
        if args:
            cmd.extend(args)
        
        try:
            result = subprocess.run(cmd, cwd=str(repo_dir))
            return result.returncode
        except subprocess.SubprocessError as e:
            print(f"Ошибка: Не удалось выполнить скрипт: {e}")
            return 1
    
    def list_repos(self):
        """Список всех клонированных репозиториев."""
        clone_dir = self.config.clone_directory
        
        if not clone_dir.exists():
            print("Репозитории еще не клонированы.")
            return []
        
        repos = []
        try:
            for d in clone_dir.iterdir():
                try:
                    if d.is_dir() and (d / ".git").exists():
                        repos.append(d.name)
                except (PermissionError, OSError):
                    # Skip directories we can't access
                    continue
        except (PermissionError, OSError) as e:
            print(f"Ошибка доступа к директории клонирования: {e}")
            return []
        
        if not repos:
            print("Репозитории еще не клонированы.")
            return []
        
        print("\nКлонированные репозитории:")
        print("-" * 40)
        for repo in sorted(repos):
            repo_path = clone_dir / repo
            print(f"  {repo} ({repo_path})")
        print("-" * 40)
        print(f"Всего: {len(repos)} репозиториев")
        
        return repos
    
    def find_shell_scripts(self, repo_path):
        """Найти все .sh файлы в репозитории."""
        repo_dir = self._get_repo_dir(repo_path)
        
        if not repo_dir.exists():
            return []
        
        scripts = []
        try:
            for root, dirs, files in os.walk(repo_dir):
                # Skip .git directory
                if '.git' in dirs:
                    dirs.remove('.git')
                
                for file in files:
                    if file.endswith('.sh'):
                        full_path = Path(root) / file
                        relative_path = full_path.relative_to(repo_dir)
                        scripts.append(str(relative_path))
        except (PermissionError, OSError) as e:
            print(f"Ошибка поиска скриптов: {e}")
            return []
        
        return sorted(scripts)


class InteractiveMenu:
    """Интерактивное меню для работы с MyGit."""
    
    def __init__(self, config):
        self.config = config
        self.repo_manager = GitHubRepo(config)
        self.ui = TerminalUI()
    
    def clear_screen(self):
        """Очистить экран консоли."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def pause(self):
        """Пауза перед возвратом в меню."""
        try:
            input(self.ui.prompt("Нажмите Enter, чтобы продолжить..."))
        except EOFError:
            pass
    
    def get_input(self, prompt):
        """Получить ввод от пользователя с обработкой EOF."""
        try:
            return input(prompt).strip()
        except EOFError:
            return ""
    
    def main_menu(self):
        """Главное меню."""
        while True:
            self.clear_screen()
            self.ui.header(
                "MyGit  /  PRIVATE REPOSITORY CONSOLE",
                "Управление репозиториями и запуск shell-скриптов",
            )
            print(f"\n  {self.ui.style('GitHub', self.ui.DIM)}      {self.ui.style(self.config.username, self.ui.CYAN)}")
            print(f"  {self.ui.style('Хранилище', self.ui.DIM)}  {self.config.clone_directory}")
            self.ui.section("ГЛАВНОЕ МЕНЮ")
            self.ui.option("1", "Репозитории на GitHub", "просмотр, клонирование и обновление")
            self.ui.option("2", "Локальные репозитории", "поиск и запуск shell-скриптов")
            self.ui.option("3", "Конфигурация", "учётная запись и каталог хранения", self.ui.MAGENTA)
            self.ui.option("0", "Выход", color=self.ui.RED)

            choice = self.get_input(self.ui.prompt("Выберите действие:"))
            
            if choice == "1":
                self.browse_github_repos()
            elif choice == "2":
                self.browse_local_repos()
            elif choice == "3":
                self.clear_screen()
                self.ui.header("КОНФИГУРАЦИЯ", "Текущие параметры подключения")
                self.config.show()
                self.pause()
            elif choice == "0":
                self.ui.status("info", "Работа завершена. До свидания!")
                break
            else:
                self.ui.status("error", "Такого пункта нет. Выберите 0, 1, 2 или 3.")
                self.pause()
    
    def browse_github_repos(self):
        """Просмотр репозиториев на GitHub."""
        self.clear_screen()
        self.ui.header("РЕПОЗИТОРИИ GITHUB", "Получение данных через GitHub API")
        self.ui.status("info", "Загружаю список репозиториев...")
        
        repos = self.repo_manager.api.get_user_repos()
        
        if repos is None:
            self.ui.status("error", "Не удалось загрузить репозитории.")
            self.pause()
            return
        
        if not repos:
            self.ui.status("warning", "Репозитории не найдены.")
            self.pause()
            return
        
        while True:
            self.clear_screen()
            self.ui.header("РЕПОЗИТОРИИ GITHUB", f"Найдено: {len(repos)}  •  выберите репозиторий для клонирования")
            
            for idx, repo in enumerate(repos, 1):
                visibility = self.ui.style("PRIVATE", self.ui.YELLOW) if repo.get('private') else self.ui.style("PUBLIC", self.ui.GREEN)
                number = self.ui.style(f"{idx:>2}.", self.ui.BOLD, self.ui.CYAN)
                print(f"  {number} {self.ui.style(repo['full_name'], self.ui.BOLD)}  {visibility}")
                description = repo.get('description') or "Без описания"
                print(self.ui.style(f"      {description}", self.ui.DIM))
                print()
            
            self.ui.option("0", "Вернуться в главное меню", color=self.ui.RED)
            
            choice = self.get_input(self.ui.prompt("Номер репозитория:"))
            
            if choice == "0":
                break
            
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(repos):
                    repo_path = repos[idx]['full_name']
                    self.ui.status("info", f"Открываю {repo_path}...")
                    result = self.repo_manager.clone(repo_path)
                    if result:
                        self.ui.status("success", "Операция успешно завершена.")
                    self.pause()
                else:
                    self.ui.status("error", "Репозитория с таким номером нет.")
                    self.pause()
            except ValueError:
                self.ui.status("error", "Введите номер репозитория.")
                self.pause()
    
    def browse_local_repos(self):
        """Просмотр локальных репозиториев."""
        while True:
            self.clear_screen()
            self.ui.header("ЛОКАЛЬНЫЕ РЕПОЗИТОРИИ", "Выберите репозиторий, чтобы открыть его скрипты")
            
            clone_dir = self.config.clone_directory
            
            if not clone_dir.exists():
                self.ui.status("warning", "Репозитории ещё не клонированы.")
                self.pause()
                return
            
            repos = []
            try:
                for d in clone_dir.iterdir():
                    if d.is_dir() and (d / ".git").exists():
                        repos.append(d.name)
            except (PermissionError, OSError) as e:
                self.ui.status("error", f"Ошибка доступа: {e}")
                self.pause()
                return
            
            if not repos:
                self.ui.status("warning", "Репозитории ещё не клонированы.")
                self.pause()
                return
            
            repos = sorted(repos)
            
            for idx, repo in enumerate(repos, 1):
                repo_path = clone_dir / repo
                number = self.ui.style(f"{idx:>2}.", self.ui.BOLD, self.ui.CYAN)
                print(f"  {number} {self.ui.style(repo, self.ui.BOLD)}")
                print(self.ui.style(f"      {repo_path}", self.ui.DIM))
                
                # Show shell scripts count
                scripts = self.repo_manager.find_shell_scripts(f"{self.config.username}/{repo}")
                if scripts:
                    print(f"      {self.ui.style('●', self.ui.GREEN)} Скриптов: {len(scripts)}")
                print()
            
            self.ui.option("0", "Вернуться в главное меню", color=self.ui.RED)
            
            choice = self.get_input(self.ui.prompt("Номер репозитория:"))
            
            if choice == "0":
                break
            
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(repos):
                    self.browse_scripts(f"{self.config.username}/{repos[idx]}")
                else:
                    self.ui.status("error", "Репозитория с таким номером нет.")
                    self.pause()
            except ValueError:
                self.ui.status("error", "Введите номер репозитория.")
                self.pause()
    
    def browse_scripts(self, repo_path):
        """Просмотр скриптов в репозитории."""
        while True:
            self.clear_screen()
            self.ui.header("SHELL-СКРИПТЫ", repo_path)
            
            scripts = self.repo_manager.find_shell_scripts(repo_path)
            
            if not scripts:
                self.ui.status("warning", "В этом репозитории нет .sh-скриптов.")
                self.pause()
                return
            
            for idx, script in enumerate(scripts, 1):
                number = self.ui.style(f"{idx:>2}.", self.ui.BOLD, self.ui.CYAN)
                print(f"  {number} {script}")
            
            self.ui.option("0", "Назад к репозиториям", color=self.ui.RED)
            
            choice = self.get_input(self.ui.prompt("Номер скрипта:"))
            
            if choice == "0":
                break
            
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(scripts):
                    script_path = scripts[idx]
                    self.ui.section("ПОДТВЕРЖДЕНИЕ ЗАПУСКА")
                    print(f"  Скрипт:      {self.ui.style(script_path, self.ui.YELLOW)}")
                    print(f"  Репозиторий: {repo_path}")
                    
                    confirm = self.get_input(self.ui.prompt("Запустить? [y/N]:")).lower()
                    
                    if confirm == 'y':
                        self.repo_manager.run_script(repo_path, script_path, no_confirm=True)
                        self.pause()
                else:
                    self.ui.status("error", "Скрипта с таким номером нет.")
                    self.pause()
            except ValueError:
                self.ui.status("error", "Введите номер скрипта.")
                self.pause()
    
def cmd_clone(args, config):
    """Обработка команды clone."""
    repo = GitHubRepo(config)
    result = repo.clone(args.repository, force=args.force)
    return 0 if result else 1


def cmd_pull(args, config):
    """Обработка команды pull."""
    repo = GitHubRepo(config)
    result = repo.pull(args.repository)
    return 0 if result else 1


def cmd_run(args, config):
    """Обработка команды run."""
    repo = GitHubRepo(config)
    return repo.run_script(args.repository, args.script, args.script_args, args.yes)


def cmd_list(args, config):
    """Обработка команды list."""
    repo = GitHubRepo(config)
    repo.list_repos()
    return 0


def cmd_config(args, config):
    """Обработка команды config."""
    config.show()
    return 0


def main():
    """Главная точка входа."""
    parser = argparse.ArgumentParser(
        description="MyGit - Коннектор приватных репозиториев GitHub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""

Примеры:
  mygit                           Запустить в интерактивном режиме
  mygit clone owner/repo          Клонировать приватный репозиторий
  mygit clone owner/repo --force  Принудительно переклонировать
  mygit pull owner/repo           Получить последние изменения
  mygit run owner/repo script.sh  Клонировать и запустить скрипт
  mygit list                      Список клонированных репозиториев
  mygit config                    Показать конфигурацию
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Доступные команды")
    
    # Clone command
    clone_parser = subparsers.add_parser("clone", help="Клонировать приватный репозиторий")
    clone_parser.add_argument("repository", help="Путь к репозиторию (owner/repo)")
    clone_parser.add_argument("-f", "--force", action="store_true",
                              help="Принудительно переклонировать если существует")
    clone_parser.set_defaults(func=cmd_clone)
    
    # Pull command
    pull_parser = subparsers.add_parser("pull", help="Получить последние изменения")
    pull_parser.add_argument("repository", help="Путь к репозиторию (owner/repo)")
    pull_parser.set_defaults(func=cmd_pull)
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Клонировать и запустить скрипт")
    run_parser.add_argument("repository", help="Путь к репозиторию (owner/repo)")
    run_parser.add_argument("script", help="Путь к скрипту в репозитории")
    run_parser.add_argument("script_args", nargs="*", help="Аргументы для скрипта")
    run_parser.add_argument("-y", "--yes", action="store_true",
                            help="Пропустить запрос подтверждения")
    run_parser.set_defaults(func=cmd_run)
    
    # List command
    list_parser = subparsers.add_parser("list", help="Список клонированных репозиториев")
    list_parser.set_defaults(func=cmd_list)
    
    # Config command
    config_parser = subparsers.add_parser("config", help="Показать конфигурацию")
    config_parser.set_defaults(func=cmd_config)
    
    args = parser.parse_args()
    
    # Load configuration
    config = Config()
    config.load()
    
    # If no command specified, run interactive menu
    if args.command is None:
        menu = InteractiveMenu(config)
        menu.main_menu()
        return 0
    
    # Execute command
    return args.func(args, config)


if __name__ == "__main__":
    sys.exit(main())
