import os
import json
import logging
from pathlib import Path
from typing import Any, Optional


class Config:
    """Configuration manager for the MCP Server with JSON-based configuration and validation."""
    
    def __init__(self, config_path: str = None, domain: str = None, environment: str = "development"):
        # Set up paths relative to project root
        self.project_root = Path(__file__).parent.parent.parent.parent
        
        # Determine config path based on domain/environment or explicit path
        if config_path:
            self.config_path = config_path
        elif domain:
            domain_config = self.project_root / "config" / "domains" / f"{domain}.json"
            base_config_path = self.project_root / "config.json"
            
            # Load and merge configs
            base_config = self._load_json_file(base_config_path) if base_config_path.exists() else {}
            domain_config_data = self._load_json_file(domain_config) if domain_config.exists() else {}
            
            # Merge domain into base config
            self._config = self._merge_configs(base_config, domain_config_data)
            self._setup_logging()
            return
        else:
            # Default to single config.json file
            self.config_path = str(self.project_root / "config.json")
        
        self._config = self._load_config()
        self._setup_logging()
    
    def _load_config(self) -> dict:
        """Load configuration from JSON file"""
        try:
            config_file = Path(self.config_path)
            if not config_file.exists():
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            logging.info(f"Configuration loaded from {self.config_path}")
            return config
        except Exception as e:
            logging.error(f"Failed to load configuration: {e}")
            # Return default configuration
            return self._get_default_config()
    
    def _get_default_config(self) -> dict:
        """Fallback default configuration"""
        return {
            "database": {
                "persist_directory": "./chroma_db_advanced",
                "collections": {
                    "short_term": "short_term_memory",
                    "long_term": "long_term_memory",
                    "consolidated": "consolidated_memory",
                    "legacy": "knowledge_base"
                }
            },
            "embeddings": {
                "model_name": "sentence-transformers/all-MiniLM-L6-v2",
                "chunk_size": 1000,
                "chunk_overlap": 100
            },
            "reranker": {
                "model_name": "cross-encoder/ms-marco-MiniLM-L-6-v2"
            },
            "memory_scoring": {
                "decay_constant": 86400,
                "max_access_count": 100,
                "importance_threshold": 0.7,
                "scoring_weights": {
                    "semantic": 0.4,
                    "recency": 0.3,
                    "frequency": 0.2,
                    "importance": 0.1
                }
            },
            "server": {
                "host": "127.0.0.1",
                "port": 8080,
                "title": "Advanced Project Memory MCP Server",
                "version": "2.0.0"
            }
        }
    
    def _setup_logging(self):
        """Setup logging based on configuration"""
        log_config = self._config.get('logging', {})
        log_file = log_config.get('file', 'logs/mcp_server.log')
        
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=getattr(logging, log_config.get('level', 'INFO')),
            format=log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(log_file)
            ]
        )
    
    def _load_json_file(self, file_path: Path) -> dict:
        """Load a JSON configuration file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.warning(f"Failed to load config file {file_path}: {e}")
            return {}
    
    def _merge_configs(self, base: dict, overlay: dict) -> dict:
        """Deep merge two configuration dictionaries"""
        result = base.copy()
        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        return result
    
    def get(self, *keys, default=None) -> Any:
        """Get nested configuration value using dot notation"""
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def get_database_config(self) -> dict:
        """Get database configuration"""
        return self.get('database', default={})
    
    def get_embeddings_config(self) -> dict:
        """Get embeddings configuration"""
        return self.get('embeddings', default={})
    
    def get_reranker_config(self) -> dict:
        """Get reranker configuration"""
        return self.get('reranker', default={})
    
    def get_memory_scoring_config(self) -> dict:
        """Get memory scoring configuration"""
        return self.get('memory_scoring', default={})
    
    def get_server_config(self) -> dict:
        """Get server configuration"""
        return self.get('server', default={})
    
    def get_ttl_config(self) -> dict:
        """Get TTL configuration"""
        return self.get('ttl', default={})
    
    def get_memory_management_config(self) -> dict:
        """Get memory management configuration"""
        return self.get('memory_management', default={})
    
    def get_lifecycle_config(self) -> dict:
        """Get lifecycle management configuration"""
        return self.get('lifecycle', default={})