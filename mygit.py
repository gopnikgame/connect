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


class GitHubRepo:
    """Менеджер операций с репозиториями GitHub."""
    
    def __init__(self, config):
        self.config = config
    
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
            # Use subprocess with capture_output to prevent credentials from appearing in output
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
        
        # Make script executable
        os.chmod(full_script_path, 0o755)
        
        # Run the script
        print(f"\nЗапуск скрипта: {script_path}")
        print("-" * 40)
        
        cmd = [str(full_script_path)]
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
    
    if args.command is None:
        parser.print_help()
        return 0
    
    # Load configuration
    config = Config()
    config.load()
    
    # Execute command
    return args.func(args, config)


if __name__ == "__main__":
    sys.exit(main())
