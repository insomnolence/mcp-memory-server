#!/usr/bin/env python3
"""
Configuration Validation Script

Validates MCP server configuration files for correctness and completeness.
"""

import json
import sys
from pathlib import Path

def validate_config(config_path: str = "config.json") -> bool:
    """Validate configuration file"""
    try:
        config_file = Path(config_path)
        if not config_file.exists():
            print(f"ERROR: Configuration file not found: {config_path}")
            return False
        
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        print(f"SUCCESS: Configuration file loaded: {config_path}")
        
        # Required sections
        required_sections = [
            'database',
            'embeddings', 
            'reranker',
            'memory_scoring',
            'server'
        ]
        
        missing_sections = []
        for section in required_sections:
            if section not in config:
                missing_sections.append(section)
        
        if missing_sections:
            print(f"ERROR: Missing required sections: {missing_sections}")
            return False
        
        # Validate specific settings
        errors = []
        
        # Database validation
        db_config = config['database']
        if 'persist_directory' not in db_config:
            errors.append("database.persist_directory is required")
        
        # Memory scoring validation
        scoring = config['memory_scoring']
        if 'scoring_weights' in scoring:
            weights = scoring['scoring_weights']
            weight_sum = sum(weights.values())
            if abs(weight_sum - 1.0) > 0.01:
                errors.append(f"scoring_weights must sum to 1.0, got {weight_sum}")
        
        # Server validation
        server = config['server']
        port = server.get('port', 8080)
        if not isinstance(port, int) or port < 1 or port > 65535:
            errors.append("server.port must be a valid port number (1-65535)")
        
        if errors:
            print("ERROR: Configuration errors found:")
            for error in errors:
                print(f"   - {error}")
            return False
        
        print("SUCCESS: Configuration validation passed!")
        print(f"Database: {db_config.get('persist_directory')}")
        print(f"Embedding model: {config['embeddings'].get('model_name')}")
        print(f"Server: {server.get('host')}:{server.get('port')}")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in configuration file: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Error validating configuration: {e}")
        return False

def main():
    """Main validation function"""
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    
    print(f"Validating MCP server configuration: {config_path}")
    print("=" * 60)
    
    if validate_config(config_path):
        print("=" * 60)
        print("Configuration is valid and ready to use!")
        sys.exit(0)
    else:
        print("=" * 60)
        print("Configuration validation failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()