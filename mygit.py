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
                print(f"Репозиторий уже существует по адресу: {repo_dir}")
                print("Используйте --force для переклонирования или обновите вручную с помощью 'git pull'")
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
            
            print(f"Успешно клонировано в: {repo_dir}")
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
        
        try:
            result = subprocess.run(
                ["git", "pull"],
                cwd=str(repo_dir),
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"Ошибка получения изменений репозитория: {result.stderr}")
                return False
            
            print(result.stdout)
            return True
            
        except subprocess.SubprocessError as e:
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
    
    def clear_screen(self):
        """Очистить экран консоли."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def pause(self):
        """Пауза перед возвратом в меню."""
        try:
            input("\nНажмите Enter для продолжения...")
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
            print("=" * 50)
            print("MyGit - Менеджер приватных репозиториев GitHub")
            print("=" * 50)
            print(f"\nПользователь: {self.config.username}")
            print(f"Директория: {self.config.clone_directory}")
            print("\n1. Просмотреть мои репозитории на GitHub")
            print("2. Клонировать репозиторий")
            print("3. Обновить репозиторий (git pull)")
            print("4. Просмотреть локальные репозитории")
            print("5. Запустить скрипт из репозитория")
            print("6. Показать конфигурацию")
            print("0. Выход")
            print("-" * 50)
            
            choice = self.get_input("Выберите действие: ")
            
            if choice == "1":
                self.browse_github_repos()
            elif choice == "2":
                self.clone_repo_interactive()
            elif choice == "3":
                self.pull_repo_interactive()
            elif choice == "4":
                self.browse_local_repos()
            elif choice == "5":
                self.run_script_interactive()
            elif choice == "6":
                self.config.show()
                self.pause()
            elif choice == "0":
                print("\nДо свидания!")
                break
            else:
                print("\nНеверный выбор. Попробуйте снова.")
                self.pause()
    
    def browse_github_repos(self):
        """Просмотр репозиториев на GitHub."""
        self.clear_screen()
        print("=" * 50)
        print("Загрузка репозиториев с GitHub...")
        print("=" * 50)
        
        repos = self.repo_manager.api.get_user_repos()
        
        if repos is None:
            print("\nНе удалось загрузить репозитории.")
            self.pause()
            return
        
        if not repos:
            print("\nРепозитории не найдены.")
            self.pause()
            return
        
        while True:
            self.clear_screen()
            print("=" * 50)
            print(f"Ваши репозитории на GitHub (всего: {len(repos)})")
            print("=" * 50)
            
            for idx, repo in enumerate(repos, 1):
                private = "🔒 " if repo.get('private') else "🔓 "
                print(f"{idx}. {private}{repo['full_name']}")
                print(f"   Описание: {repo.get('description', 'Нет описания')}")
                print()
            
            print("0. Вернуться в главное меню")
            print("-" * 50)
            
            choice = self.get_input("Выберите репозиторий для клонирования (или 0): ")
            
            if choice == "0":
                break
            
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(repos):
                    repo_path = repos[idx]['full_name']
                    print(f"\nКлонирование {repo_path}...")
                    result = self.repo_manager.clone(repo_path)
                    if result:
                        print("\nУспешно!")
                    self.pause()
                else:
                    print("\nНеверный номер репозитория.")
                    self.pause()
            except ValueError:
                print("\nПожалуйста, введите число.")
                self.pause()
    
    def clone_repo_interactive(self):
        """Интерактивное клонирование репозитория."""
        self.clear_screen()
        print("=" * 50)
        print("Клонирование репозитория")
        print("=" * 50)
        
        repo_path = self.get_input("\nВведите путь к репозиторию (owner/repo): ")
        
        if not repo_path:
            return
        
        force = self.get_input("Принудительно переклонировать? (y/N): ").lower() == 'y'
        
        result = self.repo_manager.clone(repo_path, force=force)
        if result:
            print("\nУспешно!")
        
        self.pause()
    
    def pull_repo_interactive(self):
        """Интерактивное обновление репозитория."""
        self.clear_screen()
        print("=" * 50)
        print("Обновление репозитория")
        print("=" * 50)
        
        repo_path = self.get_input("\nВведите путь к репозиторию (owner/repo): ")
        
        if not repo_path:
            return
        
        self.repo_manager.pull(repo_path)
        self.pause()
    
    def browse_local_repos(self):
        """Просмотр локальных репозиториев."""
        while True:
            self.clear_screen()
            print("=" * 50)
            print("Локальные репозитории")
            print("=" * 50)
            
            clone_dir = self.config.clone_directory
            
            if not clone_dir.exists():
                print("\nРепозитории еще не клонированы.")
                self.pause()
                return
            
            repos = []
            try:
                for d in clone_dir.iterdir():
                    if d.is_dir() and (d / ".git").exists():
                        repos.append(d.name)
            except (PermissionError, OSError) as e:
                print(f"\nОшибка доступа: {e}")
                self.pause()
                return
            
            if not repos:
                print("\nРепозитории еще не клонированы.")
                self.pause()
                return
            
            repos = sorted(repos)
            
            for idx, repo in enumerate(repos, 1):
                repo_path = clone_dir / repo
                print(f"{idx}. {repo}")
                print(f"   Путь: {repo_path}")
                
                # Show shell scripts count
                scripts = self.repo_manager.find_shell_scripts(f"{self.config.username}/{repo}")
                if scripts:
                    print(f"   📜 Найдено скриптов: {len(scripts)}")
                print()
            
            print("0. Вернуться в главное меню")
            print("-" * 50)
            
            choice = self.get_input("Выберите репозиторий для просмотра скриптов (или 0): ")
            
            if choice == "0":
                break
            
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(repos):
                    self.browse_scripts(f"{self.config.username}/{repos[idx]}")
                else:
                    print("\nНеверный номер репозитория.")
                    self.pause()
            except ValueError:
                print("\nПожалуйста, введите число.")
                self.pause()
    
    def browse_scripts(self, repo_path):
        """Просмотр скриптов в репозитории."""
        while True:
            self.clear_screen()
            print("=" * 50)
            print(f"Скрипты в репозитории: {repo_path}")
            print("=" * 50)
            
            scripts = self.repo_manager.find_shell_scripts(repo_path)
            
            if not scripts:
                print("\nСкрипты .sh не найдены в этом репозитории.")
                self.pause()
                return
            
            for idx, script in enumerate(scripts, 1):
                print(f"{idx}. {script}")
            
            print("\n0. Назад")
            print("-" * 50)
            
            choice = self.get_input("Выберите скрипт для запуска (или 0): ")
            
            if choice == "0":
                break
            
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(scripts):
                    script_path = scripts[idx]
                    print(f"\nЗапуск скрипта: {script_path}")
                    print(f"Репозиторий: {repo_path}")
                    
                    confirm = self.get_input("\nЗапустить этот скрипт? (y/N): ").lower()
                    
                    if confirm == 'y':
                        self.repo_manager.run_script(repo_path, script_path, no_confirm=True)
                        self.pause()
                else:
                    print("\nНеверный номер скрипта.")
                    self.pause()
            except ValueError:
                print("\nПожалуйста, введите число.")
                self.pause()
    
    def run_script_interactive(self):
        """Интерактивный запуск скрипта."""
        self.clear_screen()
        print("=" * 50)
        print("Запуск скрипта")
        print("=" * 50)
        
        repo_path = self.get_input("\nВведите путь к репозиторию (owner/repo): ")
        if not repo_path:
            return
        
        script_path = self.get_input("Введите путь к скрипту в репозитории: ")
        if not script_path:
            return
        
        self.repo_manager.run_script(repo_path, script_path)
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
