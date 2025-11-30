#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MyGit - Private GitHub Repository Connector

A tool for connecting to private GitHub repositories, cloning them,
and running shell scripts from them.

Designed for Ubuntu server operating systems.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


class Config:
    """Configuration manager for MyGit."""
    
    def __init__(self):
        self.config_dir = Path.home() / ".mygit"
        self.config_file = self.config_dir / "config.json"
        self._config = None
    
    def load(self):
        """Load configuration from file."""
        if not self.config_file.exists():
            print("Error: Configuration not found.")
            print("Please run the installer first: ./install.sh")
            sys.exit(1)
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid configuration file: {e}")
            sys.exit(1)
        except IOError as e:
            print(f"Error: Cannot read configuration file: {e}")
            sys.exit(1)
        
        return self._config
    
    @property
    def username(self):
        """Get GitHub username."""
        if self._config is None:
            self.load()
        return self._config.get("github_username", "")
    
    @property
    def token(self):
        """Get GitHub personal access token."""
        if self._config is None:
            self.load()
        return self._config.get("github_token", "")
    
    @property
    def clone_directory(self):
        """Get default clone directory."""
        if self._config is None:
            self.load()
        return Path(self._config.get("clone_directory", str(Path.home() / "mygit-repos")))
    
    def show(self):
        """Display current configuration (hiding sensitive data)."""
        if self._config is None:
            self.load()
        
        print("\nCurrent Configuration:")
        print("-" * 40)
        print(f"GitHub Username: {self.username}")
        print(f"GitHub Token: {'*' * 16} (configured)")
        print(f"Clone Directory: {self.clone_directory}")
        print("-" * 40)


class GitHubRepo:
    """Manager for GitHub repository operations."""
    
    def __init__(self, config):
        self.config = config
    
    def _build_clone_url(self, repo_path):
        """Build clone URL for a repository (without credentials)."""
        return f"https://github.com/{repo_path}.git"
    
    def _get_git_env(self):
        """Get environment variables for git with credentials."""
        env = os.environ.copy()
        # Use GIT_ASKPASS to provide credentials securely
        return env
    
    def _get_repo_dir(self, repo_path):
        """Get local directory path for a repository."""
        repo_name = repo_path.split("/")[-1]
        return self.config.clone_directory / repo_name
    
    def clone(self, repo_path, force=False):
        """
        Clone a private repository.
        
        Args:
            repo_path: Repository path in format 'owner/repo'
            force: If True, remove existing directory and re-clone
        
        Returns:
            Path to cloned repository or None on failure
        """
        if "/" not in repo_path:
            print("Error: Invalid repository format. Use 'owner/repo'")
            return None
        
        repo_dir = self._get_repo_dir(repo_path)
        
        # Check if already cloned
        if repo_dir.exists():
            if force:
                print(f"Removing existing directory: {repo_dir}")
                try:
                    shutil.rmtree(repo_dir)
                except OSError as e:
                    print(f"Error removing directory: {e}")
                    return None
            else:
                print(f"Repository already exists at: {repo_dir}")
                print("Use --force to re-clone or update manually with 'git pull'")
                return repo_dir
        
        # Ensure parent directory exists
        self.config.clone_directory.mkdir(parents=True, exist_ok=True)
        
        # Build authenticated URL for cloning
        clone_url = f"https://{self.config.username}:{self.config.token}@github.com/{repo_path}.git"
        print(f"Cloning {repo_path}...")
        
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
                print(f"Error cloning repository: {error_msg}")
                return None
            
            # Remove credentials from remote URL after cloning
            self._sanitize_remote_url(repo_dir, repo_path)
            
            print(f"Successfully cloned to: {repo_dir}")
            return repo_dir
            
        except subprocess.SubprocessError as e:
            print(f"Error: Failed to execute git command: {e}")
            return None
    
    def _sanitize_remote_url(self, repo_dir, repo_path):
        """Remove credentials from the remote URL in .git/config."""
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
        Pull latest changes for a repository.
        
        Args:
            repo_path: Repository path in format 'owner/repo'
        
        Returns:
            True on success, False on failure
        """
        repo_dir = self._get_repo_dir(repo_path)
        
        if not repo_dir.exists():
            print(f"Error: Repository not found at {repo_dir}")
            print("Clone it first with: mygit clone {repo_path}")
            return False
        
        print(f"Pulling latest changes for {repo_path}...")
        
        try:
            result = subprocess.run(
                ["git", "pull"],
                cwd=str(repo_dir),
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"Error pulling repository: {result.stderr}")
                return False
            
            print(result.stdout)
            return True
            
        except subprocess.SubprocessError as e:
            print(f"Error: Failed to execute git command: {e}")
            return False
    
    def run_script(self, repo_path, script_path, args=None, no_confirm=False):
        """
        Clone (if needed) and run a shell script from a repository.
        
        Args:
            repo_path: Repository path in format 'owner/repo'
            script_path: Path to script within the repository
            args: Additional arguments to pass to the script
            no_confirm: Skip confirmation prompt
        
        Returns:
            Exit code of the script
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
            print(f"Error: Script not found: {full_script_path}")
            return 1
        
        if not full_script_path.is_file():
            print(f"Error: Not a file: {full_script_path}")
            return 1
        
        # Security check: validate script path is within repository (prevent path traversal)
        try:
            full_script_path = full_script_path.resolve()
            repo_dir_resolved = repo_dir.resolve()
            if not str(full_script_path).startswith(str(repo_dir_resolved)):
                print("Error: Script path traversal detected. Operation cancelled.")
                return 1
        except (OSError, ValueError) as e:
            print(f"Error: Invalid script path: {e}")
            return 1
        
        # Require user confirmation before making file executable and running
        if not no_confirm:
            print(f"\nScript to execute: {full_script_path}")
            print(f"Repository: {repo_path}")
            try:
                confirm = input("\nAre you sure you want to run this script? [y/N]: ").strip().lower()
            except EOFError:
                confirm = 'n'
            if confirm != 'y':
                print("Operation cancelled.")
                return 0
        
        # Make script executable
        os.chmod(full_script_path, 0o755)
        
        # Run the script
        print(f"\nRunning script: {script_path}")
        print("-" * 40)
        
        cmd = [str(full_script_path)]
        if args:
            cmd.extend(args)
        
        try:
            result = subprocess.run(cmd, cwd=str(repo_dir))
            return result.returncode
        except subprocess.SubprocessError as e:
            print(f"Error: Failed to execute script: {e}")
            return 1
    
    def list_repos(self):
        """List all cloned repositories."""
        clone_dir = self.config.clone_directory
        
        if not clone_dir.exists():
            print("No repositories cloned yet.")
            return []
        
        repos = [d.name for d in clone_dir.iterdir() if d.is_dir() and (d / ".git").exists()]
        
        if not repos:
            print("No repositories cloned yet.")
            return []
        
        print("\nCloned Repositories:")
        print("-" * 40)
        for repo in sorted(repos):
            repo_path = clone_dir / repo
            print(f"  {repo} ({repo_path})")
        print("-" * 40)
        print(f"Total: {len(repos)} repository(ies)")
        
        return repos


def cmd_clone(args, config):
    """Handle clone command."""
    repo = GitHubRepo(config)
    result = repo.clone(args.repository, force=args.force)
    return 0 if result else 1


def cmd_pull(args, config):
    """Handle pull command."""
    repo = GitHubRepo(config)
    result = repo.pull(args.repository)
    return 0 if result else 1


def cmd_run(args, config):
    """Handle run command."""
    repo = GitHubRepo(config)
    return repo.run_script(args.repository, args.script, args.script_args, args.yes)


def cmd_list(args, config):
    """Handle list command."""
    repo = GitHubRepo(config)
    repo.list_repos()
    return 0


def cmd_config(args, config):
    """Handle config command."""
    config.show()
    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="MyGit - Private GitHub Repository Connector",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  mygit clone owner/repo          Clone a private repository
  mygit clone owner/repo --force  Force re-clone
  mygit pull owner/repo           Pull latest changes
  mygit run owner/repo script.sh  Clone and run a script
  mygit list                      List cloned repositories
  mygit config                    Show configuration
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Clone command
    clone_parser = subparsers.add_parser("clone", help="Clone a private repository")
    clone_parser.add_argument("repository", help="Repository path (owner/repo)")
    clone_parser.add_argument("-f", "--force", action="store_true",
                              help="Force re-clone if exists")
    clone_parser.set_defaults(func=cmd_clone)
    
    # Pull command
    pull_parser = subparsers.add_parser("pull", help="Pull latest changes")
    pull_parser.add_argument("repository", help="Repository path (owner/repo)")
    pull_parser.set_defaults(func=cmd_pull)
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Clone and run a script")
    run_parser.add_argument("repository", help="Repository path (owner/repo)")
    run_parser.add_argument("script", help="Path to script in repository")
    run_parser.add_argument("script_args", nargs="*", help="Arguments for the script")
    run_parser.add_argument("-y", "--yes", action="store_true",
                            help="Skip confirmation prompt")
    run_parser.set_defaults(func=cmd_run)
    
    # List command
    list_parser = subparsers.add_parser("list", help="List cloned repositories")
    list_parser.set_defaults(func=cmd_list)
    
    # Config command
    config_parser = subparsers.add_parser("config", help="Show configuration")
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
