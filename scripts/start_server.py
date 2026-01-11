#!/usr/bin/env python3
"""
Enhanced MCP Server Startup Script

This script starts the MCP server using configuration from config.json
"""

import sys
import os
import uvicorn
from pathlib import Path

# Add src directory to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from mcp_memory_server.config import Config

def main():
    """Start the refactored MCP server with configuration"""
    # Check for help flag
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
        print("MCP Memory Server - Start Script")
        print()
        print("Usage:")
        print("  python scripts/start_server.py                    # Start with config.json")
        print("  MCP_CONFIG_FILE=custom.json python scripts/start_server.py")
        print("  MCP_DOMAIN=business-development python scripts/start_server.py")
        print()
        print("Environment Variables:")
        print("  MCP_CONFIG_FILE    Path to configuration file")
        print("  MCP_DOMAIN         Domain-specific configuration to use")
        print()
        print("Available domains: business-development, research, creative-writing, cooking")
        return
    
    # Support environment variables for configuration
    config_file = os.environ.get('MCP_CONFIG_FILE')
    domain = os.environ.get('MCP_DOMAIN')
    
    config = Config(config_path=config_file, domain=domain)
    server_config = config.get_server_config()

    host = server_config.get('host', '127.0.0.1')
    port = server_config.get('port', 8080)

    print(f"Starting Enhanced MCP Memory Server")
    if domain:
        print(f"Domain configuration: {domain}")
    elif config_file:
        print(f"Configuration loaded from: {config_file}")
    elif hasattr(config, 'config_path'):
        print(f"Configuration loaded from: {config.config_path}")
    else:
        print(f"Using default configuration")
    print(f"Database location: {config.get('database', 'persist_directory')}")
    print(f"Embedding model: {config.get('embeddings', 'model_name')}")
    print(f"Server starting on: http://{host}:{port}")
    print(f"Logs will be written to: {config.get('logging', 'file', default='mcp_server.log')}")
    print("Architecture: Modular (config, memory, tools, server)")
    print("=" * 60)
    
    # Start the server
    uvicorn.run(
        "mcp_memory_server.main:app",  # Use import string for reload capability
        host=host,
        port=port,
        reload=False,  # Enable auto-reload for development
        log_level=config.get('logging', 'level', default='info').lower()
    )

if __name__ == "__main__":
    main()
