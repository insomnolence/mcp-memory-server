#!/usr/bin/env python3
"""
Enhanced MCP Server Startup Script

This script starts the MCP server using configuration from config.json
"""

import sys
import uvicorn
from pathlib import Path

# Add src directory to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from mcp_memory_server.main import app
from mcp_memory_server.config import Config

def main():
    """Start the refactored MCP server with configuration"""
    config = Config()
    server_config = config.get_server_config()
    
    host = server_config.get('host', '127.0.0.1')
    port = server_config.get('port', 8080)
    
    print(f"🚀 Starting Enhanced MCP Memory Server (Refactored)")
    print(f"📊 Configuration loaded from: {config.config_path}")
    print(f"🗄️  Database location: {config.get('database', 'persist_directory')}")
    print(f"🧠 Embedding model: {config.get('embeddings', 'model_name')}")
    print(f"🏃 Server starting on: http://{host}:{port}")
    print(f"📝 Logs will be written to: {config.get('logging', 'file', default='mcp_server.log')}")
    print("🏗️  Architecture: Modular (config, memory, tools, server)")
    print("=" * 60)
    
    # Start the server
    uvicorn.run(
        app,  # Use imported app
        host=host,
        port=port,
        reload=True,  # Enable auto-reload for development
        log_level=config.get('logging', 'level', default='info').lower()
    )

if __name__ == "__main__":
    main()