#!/usr/bin/env python3
"""
Quick Setup Script for MCP Memory Server

This script provides quick setup options for common use cases without
going through the full wizard. Useful for testing and rapid deployment.

Usage:
    python scripts/quick_setup.py [template_name]

Available templates:
    development  - Optimized for software development
    research     - Optimized for research and analysis  
    creative     - Optimized for creative work
    business     - Optimized for business operations
    minimal      - Minimal resource usage
    maximum      - Maximum retention

Examples:
    python scripts/quick_setup.py development
    python scripts/quick_setup.py --list
    python scripts/quick_setup.py --help
"""

import sys
import json
import argparse
from pathlib import Path

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from wizard.templates import ConfigTemplates
from wizard.mappers import ConfigMapper
from wizard.validators import ConfigValidator
from wizard.ui import WizardUI


def create_config_from_template(template_name: str, output_file: str = "config.json") -> bool:
    """Create a configuration file from a template."""
    ui = WizardUI()
    
    # Get available templates
    available_templates = ConfigTemplates.get_available_templates()
    
    if template_name not in available_templates:
        ui.print_error(f"Unknown template: {template_name}")
        ui.print_info("Available templates:")
        for name, description in available_templates.items():
            print(f"  {name:12} - {description}")
        return False
    
    # Get base config and merge with template
    mapper = ConfigMapper()
    base_config = mapper._get_base_config()
    template_config = ConfigTemplates.get_template(template_name)
    
    # Deep merge template into base config
    config = deep_merge(base_config, template_config)
    
    # Validate the configuration
    validator = ConfigValidator()
    is_valid, errors = validator.validate_config(config)
    
    if not is_valid:
        ui.print_error("Generated configuration has validation errors:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    # Save configuration
    try:
        config_path = Path(output_file)
        
        # Create backup if file exists
        if config_path.exists():
            backup_path = config_path.with_suffix(config_path.suffix + '.backup')
            config_path.rename(backup_path)
            ui.print_info(f"Backup created: {backup_path}")
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        ui.print_success(f"Configuration created: {config_path}")
        ui.print_info(f"Template used: {template_name} - {available_templates[template_name]}")
        
        # Show next steps
        print("\nNext steps:")
        print(f"1. Review config: python scripts/setup_wizard.py --analyze --config-file {output_file}")
        print(f"2. Start server: python scripts/start_server.py")
        print(f"3. Test setup with client examples in client-examples/")
        
        return True
        
    except Exception as e:
        ui.print_error(f"Failed to save configuration: {e}")
        return False


def deep_merge(base: dict, overlay: dict) -> dict:
    """Deep merge two dictionaries."""
    result = base.copy()
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def list_templates():
    """List available templates with descriptions."""
    ui = WizardUI()
    ui.print_header("Available Configuration Templates")
    
    templates = ConfigTemplates.get_available_templates()
    
    for name, description in templates.items():
        print(f"{name:12} - {description}")
    
    print(f"\nUsage: python {Path(__file__).name} [template_name]")


def main():
    """Main entry point for quick setup."""
    parser = argparse.ArgumentParser(
        description="Quick Setup Script for MCP Memory Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "template",
        nargs="?",
        help="Template name to use for configuration"
    )
    
    parser.add_argument(
        "--list",
        action="store_true", 
        help="List available templates"
    )
    
    parser.add_argument(
        "--output",
        "-o",
        default="config.json",
        help="Output configuration file (default: config.json)"
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_templates()
        return
    
    if not args.template:
        ui = WizardUI()
        ui.print_error("Template name required")
        ui.print_info("Use --list to see available templates")
        ui.print_info("Use --help for more information")
        sys.exit(1)
    
    success = create_config_from_template(args.template, args.output)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()