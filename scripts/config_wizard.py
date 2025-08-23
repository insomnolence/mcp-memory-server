#!/usr/bin/env python3
"""
Enhanced MCP Memory Server Configuration Wizard

A comprehensive, professional wizard that guides users through configuring
their MCP Memory Server with template support, server configuration, 
domain customization, and advanced options.
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# Add wizard modules to path
sys.path.insert(0, str(Path(__file__).parent / "wizard"))

from wizard.ui import WizardUI, Colors
from wizard.questions import QuestionFlow, Question
from wizard.mappers import ConfigMapper
from wizard.validators import ConfigValidator, ConfigPreview
from wizard.templates import ConfigTemplates


class EnhancedConfigWizard:
    """Enhanced configuration wizard with professional UI and comprehensive features."""
    
    def __init__(self):
        self.ui = WizardUI(use_colors=True)
        self.question_flow = QuestionFlow()
        self.config_mapper = ConfigMapper()
        self.validator = ConfigValidator()
        self.preview = ConfigPreview()
        self.project_root = Path(__file__).parent.parent
        
    def run(self):
        """Main wizard execution flow."""
        try:
            self._display_welcome()
            
            # Check for existing configuration
            existing_config = self._load_existing_config()
            if existing_config and not self._confirm_new_configuration():
                return
            
            # Collect configuration answers
            answers = self._collect_answers()
            
            # Generate configuration
            config = self._generate_configuration(answers)
            
            # Validate configuration
            if not self._validate_configuration(config):
                return
            
            # Preview and confirm
            if not self._preview_and_confirm(config, answers):
                return
            
            # Save configuration
            self._save_configuration(config)
            
            self._display_completion()
            
        except KeyboardInterrupt:
            self.ui.print_warning("\nConfiguration cancelled by user.")
            sys.exit(0)
        except Exception as e:
            self.ui.print_error(f"Unexpected error: {e}")
            sys.exit(1)
    
    def _display_welcome(self):
        """Display welcome message and wizard overview."""
        self.ui.print_header("MCP Memory Server - Configuration Wizard")
        
        print("Welcome to the Enhanced MCP Memory Server Configuration Wizard!")
        print()
        print("This wizard will help you configure your memory server through simple")
        print("questions rather than complex technical parameters.")
        print()
        
        self.ui.print_section("What You Can Configure")
        print("• Memory retention and importance strategies")
        print("• Server accessibility and network settings")
        print("• Domain-specific keyword recognition")
        print("• Performance vs. accuracy preferences")
        print("• Storage and maintenance options")
        print("• Advanced features (optional)")
        print()
        
        print("The wizard takes about 5-10 minutes depending on your choices.")
        print("You can use templates for quick setup or customize everything.")
        print()
        
        if not self.ui.confirm_action("Ready to begin configuration?", default=True):
            print("Configuration cancelled.")
            sys.exit(0)
    
    def _load_existing_config(self) -> Optional[Dict[str, Any]]:
        """Load existing configuration if present."""
        config_path = self.project_root / "config.json"
        if not config_path.exists():
            return None
            
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            self.ui.print_info("Found existing configuration file")
            
            # Analyze existing config
            from wizard.mappers import ConfigAnalyzer
            analyzer = ConfigAnalyzer()
            analysis = analyzer.analyze_config(config)
            
            print("\nCurrent configuration:")
            for key, description in analysis.items():
                print(f"  • {key.title().replace('_', ' ')}: {description}")
            
            return config
            
        except Exception as e:
            self.ui.print_warning(f"Could not load existing config: {e}")
            return None
    
    def _confirm_new_configuration(self) -> bool:
        """Confirm whether to create new configuration."""
        return self.ui.confirm_action(
            "\nWould you like to create a new configuration?", 
            default=False
        )
    
    def _collect_answers(self) -> Dict[str, Any]:
        """Collect all wizard answers through the question flow."""
        answers = {}
        current_question = self.question_flow.get_first_question()
        question_count = 1
        
        while current_question:
            # Calculate total applicable questions for progress
            applicable_questions = self.question_flow.get_applicable_questions(answers)
            total_questions = len(applicable_questions)
            
            # Ask the current question
            answer = self.ui.ask_question(current_question, question_count, total_questions)
            answers[current_question.id] = answer
            
            # Get next question
            current_question = self.question_flow.get_next_question(current_question.id, answers)
            question_count += 1
        
        return answers
    
    def _generate_configuration(self, answers: Dict[str, Any]) -> Dict[str, Any]:
        """Generate technical configuration from answers."""
        self.ui.print_section("Generating Configuration")
        
        # Show progress
        self.ui.display_progress(1, 3, "Processing answers")
        config = self.config_mapper.map_answers_to_config(answers)
        
        self.ui.display_progress(2, 3, "Applying optimizations")
        # Apply any final optimizations
        
        self.ui.display_progress(3, 3, "Configuration complete")
        self.ui.clear_progress()
        
        self.ui.print_success("Configuration generated successfully")
        return config
    
    def _validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validate the generated configuration."""
        self.ui.print_section("Validating Configuration")
        
        is_valid, errors = self.validator.validate_config(config)
        
        if not is_valid:
            self.ui.print_error("Configuration validation failed:")
            self.ui.display_validation_errors(errors)
            return False
        
        self.ui.print_success("Configuration validation passed")
        return True
    
    def _preview_and_confirm(self, config: Dict[str, Any], answers: Dict[str, Any]) -> bool:
        """Show configuration preview and get user confirmation."""
        self.ui.print_section("Configuration Preview")
        
        # Generate comprehensive preview
        preview_data = self.preview.generate_preview(config, answers)
        self.ui.display_preview(preview_data)
        
        # Show key technical details
        print(f"\n{self.ui._colorize('Technical Details:', Colors.BOLD)}")
        print(f"  • Host: {config['server']['host']}:{config['server']['port']}")
        print(f"  • Data directory: {config['database']['persist_directory']}")
        print(f"  • Importance threshold: {config['memory_scoring']['importance_threshold']}")
        
        # Custom domain patterns
        custom_patterns = [k for k in config['memory_scoring']['domain_patterns']['patterns'].keys() 
                          if k.startswith('custom_')]
        if custom_patterns:
            print(f"  • Custom domain patterns: {len(custom_patterns)} categories")
        
        print()
        
        # Confirm save
        return self.ui.confirm_action("Save this configuration?", default=True)
    
    def _save_configuration(self, config: Dict[str, Any]):
        """Save the configuration with backup handling."""
        config_path = self.project_root / "config.json"
        
        # Create backup if existing file exists
        if config_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = config_path.parent / f"config.json.backup_{timestamp}"
            config_path.rename(backup_path)
            self.ui.print_info(f"Existing config backed up to: {backup_path.name}")
        
        # Ensure directories exist
        config_path.parent.mkdir(parents=True, exist_ok=True)
        data_dir = Path(config['database']['persist_directory'])
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create logs directory
        if 'logging' in config and 'file' in config['logging']:
            log_path = Path(config['logging']['file'])
            log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write configuration
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2, sort_keys=True)
        
        self.ui.print_success(f"Configuration saved to: {config_path}")
    
    def _display_completion(self):
        """Display completion message and next steps."""
        self.ui.print_header("Configuration Complete!")
        
        print("Your MCP Memory Server has been successfully configured!")
        print()
        
        self.ui.print_section("Next Steps")
        print("1. Start your memory server:")
        print(f"   {self.ui._colorize('python3 scripts/start_server.py', Colors.CYAN)}")
        print()
        print("2. Test the configuration:")
        print(f"   {self.ui._colorize('python3 scripts/validate_config.py', Colors.CYAN)}")
        print()
        print("3. Configure your MCP client to connect to:")
        server_config = self._get_server_config()
        print(f"   Host: {self.ui._colorize(server_config['host'], Colors.YELLOW)}")
        print(f"   Port: {self.ui._colorize(str(server_config['port']), Colors.YELLOW)}")
        print()
        
        self.ui.print_section("Additional Resources")
        print("• Documentation: docs/configuration.md")
        print("• Client examples: client-examples/")
        print("• Reconfigure anytime: python3 scripts/config_wizard.py")
        print()
        
        self.ui.print_success("Happy memory management!")
    
    def _get_server_config(self) -> Dict[str, Any]:
        """Get server configuration for display."""
        config_path = self.project_root / "config.json"
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            return config.get('server', {'host': '127.0.0.1', 'port': 8081})
        except:
            return {'host': '127.0.0.1', 'port': 8081}


class TemplateWizard:
    """Simplified wizard for quick template-based setup."""
    
    def __init__(self):
        self.ui = WizardUI(use_colors=True)
        self.project_root = Path(__file__).parent.parent
    
    def run(self):
        """Run template-based quick setup."""
        self.ui.print_header("Quick Setup - Template Selection")
        
        print("Choose from pre-configured templates for instant setup:")
        print()
        
        templates = ConfigTemplates.get_available_templates()
        template_options = []
        
        for i, (key, description) in enumerate(templates.items(), 1):
            template_options.append(key)
            recommended = " (recommended)" if key == "development" else ""
            print(f"  {i}. {key.title()}{recommended}")
            print(f"     {description}")
            print()
        
        # Get template choice
        while True:
            try:
                choice = input(f"Select template (1-{len(template_options)}): ").strip()
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(template_options):
                    template_name = template_options[choice_idx]
                    break
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a number.")
            except KeyboardInterrupt:
                print("\nSetup cancelled.")
                return
            except EOFError:
                print("\nNo input available. Using default template: development")
                template_name = "development"
                break
        
        # Generate and save configuration
        base_config = ConfigMapper().base_config
        template_config = ConfigTemplates.get_template(template_name)
        
        # Merge configurations
        config = self._merge_configs(base_config, template_config)
        
        # Save configuration
        self._save_configuration(config)
        
        self.ui.print_success(f"Template '{template_name}' configured successfully!")
        print(f"\nStart your server with: {self.ui._colorize('python3 scripts/start_server.py', Colors.CYAN)}")
    
    def _merge_configs(self, base: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """Merge template configuration into base configuration."""
        import copy
        merged = copy.deepcopy(base)
        
        def deep_merge(target: Dict[str, Any], source: Dict[str, Any]):
            for key, value in source.items():
                if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                    deep_merge(target[key], value)
                else:
                    target[key] = value
        
        deep_merge(merged, template)
        return merged
    
    def _save_configuration(self, config: Dict[str, Any]):
        """Save the template configuration."""
        config_path = self.project_root / "config.json"
        
        # Create backup if existing file exists
        if config_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = config_path.parent / f"config.json.backup_{timestamp}"
            config_path.rename(backup_path)
            self.ui.print_info(f"Existing config backed up to: {backup_path.name}")
        
        # Write configuration
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2, sort_keys=True)


def main():
    """Main entry point with setup mode selection."""
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode in ['--template', '-t', 'template', 'quick']:
            # Quick template setup
            wizard = TemplateWizard()
            wizard.run()
            return
        elif mode in ['--non-interactive', '-n', 'auto']:
            # Non-interactive mode for testing
            print("Running in non-interactive mode with defaults...")
            wizard = EnhancedConfigWizard()
            wizard.ui.use_colors = False  # Disable colors for cleaner output
            wizard.run()
            return
        elif mode in ['--help', '-h', 'help']:
            print("MCP Memory Server Configuration Wizard")
            print()
            print("Usage:")
            print("  python3 scripts/config_wizard.py              # Full interactive wizard")
            print("  python3 scripts/config_wizard.py template     # Quick template setup")
            print("  python3 scripts/config_wizard.py --non-interactive  # Auto-config with defaults")
            print("  python3 scripts/config_wizard.py --help       # Show this help")
            return
    
    # Full interactive wizard
    wizard = EnhancedConfigWizard()
    wizard.run()


if __name__ == "__main__":
    main()