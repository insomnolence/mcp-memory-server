"""
CLI interface utilities for the configuration wizard.

This module provides user interface components for displaying questions,
collecting answers, and presenting configuration previews.
"""

import sys
import json
from typing import Any, List, Dict, Optional, Tuple
from .questions import Question, QuestionType, QuestionOption


class Colors:
    """ANSI color codes for terminal output."""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Text colors
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Background colors
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'


class WizardUI:
    """User interface for the configuration wizard."""
    
    def __init__(self, use_colors: bool = True):
        self.use_colors = use_colors and self._supports_color()
        self.width = 80  # Terminal width for formatting
    
    def _supports_color(self) -> bool:
        """Check if terminal supports color output."""
        return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
    
    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text if colors are enabled."""
        if not self.use_colors:
            return text
        return f"{color}{text}{Colors.RESET}"
    
    def print_header(self, title: str):
        """Print a formatted header."""
        border = "=" * self.width
        print(f"\n{self._colorize(border, Colors.CYAN)}")
        print(f"{self._colorize(title.center(self.width), Colors.BOLD + Colors.CYAN)}")
        print(f"{self._colorize(border, Colors.CYAN)}\n")
    
    def print_section(self, title: str):
        """Print a section header."""
        print(f"\n{self._colorize('▶ ' + title, Colors.BOLD + Colors.BLUE)}")
        print(f"{self._colorize('-' * (len(title) + 2), Colors.BLUE)}")
    
    def print_question(self, question: Question, question_num: int, total_questions: int):
        """Display a question with formatting."""
        progress = f"[{question_num}/{total_questions}]"
        
        print(f"\n{self._colorize(progress, Colors.DIM)} {self._colorize(question.title, Colors.BOLD)}")
        
        if question.description:
            print(f"{self._colorize(question.description, Colors.DIM)}")
        
        if question.impact_explanation:
            print(f"{self._colorize('💡 ' + question.impact_explanation, Colors.YELLOW)}")
    
    def display_options(self, options: List[QuestionOption]) -> None:
        """Display question options with formatting."""
        print()
        for i, option in enumerate(options, 1):
            prefix = f"  {i})"
            recommended = " (recommended)" if option.recommended else ""
            
            print(f"{self._colorize(prefix, Colors.CYAN)} {self._colorize(option.display + recommended, Colors.WHITE)}")
            if option.help_text:
                print(f"     {self._colorize(option.help_text, Colors.DIM)}")
            print()
    
    def get_choice_input(self, options: List[QuestionOption], allow_multiple: bool = False) -> Any:
        """Get user choice from options."""
        while True:
            if allow_multiple:
                prompt = f"Select one or more options (1-{len(options)}, comma-separated, or 'none'): "
            else:
                prompt = f"Choose an option (1-{len(options)}): "
            
            try:
                user_input = input(self._colorize(prompt, Colors.GREEN)).strip()
                
                if allow_multiple and user_input.lower() == 'none':
                    return []
                
                if allow_multiple:
                    # Parse comma-separated choices
                    choices = []
                    for choice_str in user_input.split(','):
                        choice_num = int(choice_str.strip())
                        if 1 <= choice_num <= len(options):
                            choices.append(options[choice_num - 1].key)
                        else:
                            raise ValueError(f"Invalid choice: {choice_num}")
                    return choices
                else:
                    # Single choice
                    choice_num = int(user_input)
                    if 1 <= choice_num <= len(options):
                        return options[choice_num - 1].key
                    else:
                        raise ValueError(f"Invalid choice: {choice_num}")
                        
            except (ValueError, IndexError) as e:
                print(self._colorize(f"❌ Invalid input: {e}. Please try again.", Colors.RED))
            except EOFError:
                # Handle non-interactive environments
                if allow_multiple:
                    print(self._colorize("\nNo input available. Using empty selection.", Colors.YELLOW))
                    return []
                else:
                    # Use first recommended option or first option as default
                    default_option = next((opt for opt in options if opt.recommended), options[0])
                    print(self._colorize(f"\nNo input available. Using default: {default_option.display}", Colors.YELLOW))
                    return default_option.key
    
    def get_numeric_input(self, question: Question) -> float:
        """Get numeric input with validation."""
        validation = question.validation or {}
        min_val = validation.get("min")
        max_val = validation.get("max")
        step = validation.get("step", 0.1)
        
        prompt_parts = [f"Enter a number"]
        if min_val is not None and max_val is not None:
            prompt_parts.append(f"({min_val}-{max_val})")
        elif min_val is not None:
            prompt_parts.append(f"(≥{min_val})")
        elif max_val is not None:
            prompt_parts.append(f"(≤{max_val})")
        
        if question.default is not None:
            prompt_parts.append(f"[default: {question.default}]")
        
        prompt = " ".join(prompt_parts) + ": "
        
        while True:
            try:
                user_input = input(self._colorize(prompt, Colors.GREEN)).strip()
                
                if not user_input and question.default is not None:
                    return question.default
                
                value = float(user_input)
                
                if min_val is not None and value < min_val:
                    raise ValueError(f"Value must be at least {min_val}")
                if max_val is not None and value > max_val:
                    raise ValueError(f"Value must be at most {max_val}")
                
                return value
                
            except ValueError as e:
                print(self._colorize(f"❌ Invalid input: {e}. Please try again.", Colors.RED))
            except EOFError:
                if question.default is not None:
                    print(self._colorize(f"\nNo input available. Using default: {question.default}", Colors.YELLOW))
                    return question.default
                else:
                    print(self._colorize(f"\nNo input available. Using minimum allowed value: {min_val or 0}", Colors.YELLOW))
                    return min_val or 0
    
    def get_boolean_input(self, question: Question) -> bool:
        """Get yes/no input."""
        default_text = ""
        if question.default is not None:
            default_text = f" [default: {'yes' if question.default else 'no'}]"
        
        prompt = f"Enter yes/no{default_text}: "
        
        while True:
            try:
                user_input = input(self._colorize(prompt, Colors.GREEN)).strip().lower()
                
                if not user_input and question.default is not None:
                    return question.default
                
                if user_input in ['y', 'yes', 'true', '1']:
                    return True
                elif user_input in ['n', 'no', 'false', '0']:
                    return False
                else:
                    print(self._colorize("❌ Please enter 'yes' or 'no'.", Colors.RED))
            except EOFError:
                default_value = question.default if question.default is not None else False
                print(self._colorize(f"\nNo input available. Using default: {'yes' if default_value else 'no'}", Colors.YELLOW))
                return default_value
    
    def get_text_input(self, question: Question) -> str:
        """Get text input."""
        default_text = f" [default: {question.default}]" if question.default else ""
        prompt = f"Enter text{default_text}: "
        
        try:
            user_input = input(self._colorize(prompt, Colors.GREEN)).strip()
            
            if not user_input and question.default is not None:
                return question.default
            
            return user_input
        except EOFError:
            default_value = question.default if question.default is not None else ""
            print(self._colorize(f"\nNo input available. Using default: '{default_value}'", Colors.YELLOW))
            return default_value
    
    def ask_question(self, question: Question, question_num: int, total_questions: int) -> Any:
        """Ask a complete question and return the answer."""
        self.print_question(question, question_num, total_questions)
        
        if question.question_type == QuestionType.CHOICE:
            self.display_options(question.options)
            return self.get_choice_input(question.options)
        
        elif question.question_type == QuestionType.MULTIPLE_CHOICE:
            self.display_options(question.options)
            return self.get_choice_input(question.options, allow_multiple=True)
        
        elif question.question_type == QuestionType.NUMERIC:
            return self.get_numeric_input(question)
        
        elif question.question_type == QuestionType.BOOLEAN:
            return self.get_boolean_input(question)
        
        elif question.question_type == QuestionType.TEXT:
            return self.get_text_input(question)
        
        else:
            raise ValueError(f"Unsupported question type: {question.question_type}")
    
    def display_preview(self, preview: Dict[str, Any]):
        """Display configuration preview."""
        self.print_section("Configuration Preview")
        
        # Summary
        if "summary" in preview:
            print(f"{self._colorize('Summary:', Colors.BOLD)}")
            print(f"  {preview['summary']}\n")
        
        # Memory behavior
        if "memory_behavior" in preview:
            print(f"{self._colorize('Memory Behavior:', Colors.BOLD)}")
            for key, value in preview["memory_behavior"].items():
                print(f"  • {value}")
            print()
        
        # Performance impact
        if "performance_impact" in preview:
            print(f"{self._colorize('Performance Impact:', Colors.BOLD)}")
            for key, value in preview["performance_impact"].items():
                print(f"  • {value}")
            print()
        
        # Storage usage
        if "storage_usage" in preview:
            print(f"{self._colorize('Storage Usage:', Colors.BOLD)}")
            for key, value in preview["storage_usage"].items():
                print(f"  • {value}")
            print()
        
        # Examples
        if "examples" in preview:
            print(f"{self._colorize('Example Scenarios:', Colors.BOLD)}")
            for key, value in preview["examples"].items():
                print(f"  • {value}")
            print()
    
    def display_validation_errors(self, errors: List[str]):
        """Display configuration validation errors."""
        if not errors:
            return
        
        print(f"\n{self._colorize('⚠️  Configuration Validation Errors:', Colors.RED + Colors.BOLD)}")
        for error in errors:
            print(f"  {self._colorize('❌ ' + error, Colors.RED)}")
        print()
    
    def confirm_action(self, message: str, default: bool = False) -> bool:
        """Ask for confirmation."""
        default_text = " [Y/n]" if default else " [y/N]"
        prompt = f"{message}{default_text}: "
        
        while True:
            try:
                user_input = input(self._colorize(prompt, Colors.YELLOW)).strip().lower()
                
                if not user_input:
                    return default
                
                if user_input in ['y', 'yes']:
                    return True
                elif user_input in ['n', 'no']:
                    return False
                else:
                    print(self._colorize("Please enter 'y' or 'n'.", Colors.RED))
            except EOFError:
                print(self._colorize(f"\nNo input available. Using default: {'yes' if default else 'no'}", Colors.YELLOW))
                return default
    
    def display_progress(self, current: int, total: int, message: str = ""):
        """Display progress indicator."""
        percentage = (current / total) * 100
        filled = int(percentage / 5)  # 20 characters total
        bar = "█" * filled + "░" * (20 - filled)
        
        progress_text = f"Progress: [{bar}] {percentage:.0f}% ({current}/{total})"
        if message:
            progress_text += f" - {message}"
        
        print(f"\r{self._colorize(progress_text, Colors.CYAN)}", end="", flush=True)
    
    def clear_progress(self):
        """Clear the progress line."""
        print("\r" + " " * 80 + "\r", end="", flush=True)
    
    def print_success(self, message: str):
        """Print success message."""
        print(f"{self._colorize('✅ ' + message, Colors.GREEN)}")
    
    def print_warning(self, message: str):
        """Print warning message."""
        print(f"{self._colorize('⚠️  ' + message, Colors.YELLOW)}")
    
    def print_error(self, message: str):
        """Print error message."""
        print(f"{self._colorize('❌ ' + message, Colors.RED)}")
    
    def print_info(self, message: str):
        """Print info message."""
        print(f"{self._colorize('ℹ️  ' + message, Colors.BLUE)}")
    
    def save_config_dialog(self) -> Tuple[str, bool]:
        """Dialog for saving configuration."""
        print(f"\n{self._colorize('Save Configuration', Colors.BOLD)}")
        
        # Get filename
        default_path = "config.json"
        try:
            filename = input(f"Enter filename [{default_path}]: ").strip()
            if not filename:
                filename = default_path
        except EOFError:
            print(self._colorize(f"\nNo input available. Using default filename: {default_path}", Colors.YELLOW))
            filename = default_path
        
        # Check if file exists
        from pathlib import Path
        if Path(filename).exists():
            overwrite = self.confirm_action(f"File '{filename}' already exists. Overwrite?", default=False)
            if not overwrite:
                return self.save_config_dialog()  # Ask again
        
        # Ask about backup
        backup = self.confirm_action("Create backup of existing config?", default=True)
        
        return filename, backup