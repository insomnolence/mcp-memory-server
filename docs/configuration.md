# MCP Memory Server - Configuration Guide

## Quick Start

The MCP Memory Server uses a single configuration file (`config.json`) with optional domain-specific overrides for different use cases.

### Simple Setup
```bash
# Use default configuration
python scripts/start_server.py

# Use domain-specific configuration
MCP_DOMAIN=business-development python scripts/start_server.py
```

### Available Domains
- `business-development` - Revenue, deals, KPIs, market intelligence
- `research` - Academic research, methodology, findings, evidence
- `creative-writing` - Characters, plot, dialogue, world-building
- `cooking` - Recipes, techniques, ingredients, innovations

## Configuration Architecture

### Directory Structure
```
config/
├── domains/                    # Domain-specific configurations
│   ├── business-development.json
│   ├── creative-writing.json
│   ├── research.json
│   └── cooking.json
└── config.example.json         # Base configuration template
```

### Configuration Loading Priority
1. **Environment Variable**: `MCP_CONFIG_FILE` (highest priority)
2. **Domain Configuration**: `MCP_DOMAIN` environment variable
3. **Default**: `config.json` in project root

## Core Configuration Sections

### Server Configuration
```json
{
  "server": {
    "host": "127.0.0.1",
    "port": 8080,
    "title": "MCP Memory Server",
    "version": "2.0.0",
    "protocol_version": "2025-06-18"
  }
}
```

### Database Configuration
```json
{
  "database": {
    "persist_directory": "./chroma_db_advanced",
    "collections": {
      "short_term": "short_term_memory",
      "long_term": "long_term_memory"
    }
  }
}
```

### Embeddings Configuration
```json
{
  "embeddings": {
    "model_name": "sentence-transformers/all-MiniLM-L6-v2",
    "chunk_size": 1000,
    "chunk_overlap": 100
  },
  "reranker": {
    "model_name": "cross-encoder/ms-marco-MiniLM-L-6-v2"
  }
}
```

## Memory Management Configuration

### Importance Scoring
```json
{
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
  }
}
```

### Memory Thresholds
```json
{
  "memory_management": {
    "short_term_max_size": 100,
    "short_term_threshold": 0.4,
    "long_term_threshold": 0.7
  }
}
```

### TTL Configuration
```json
{
  "lifecycle": {
    "ttl": {
      "high_frequency_base": 1800,      # 30 minutes
      "high_frequency_jitter": 300,     # 5 minutes
      "medium_frequency_base": 18000,   # 5 hours
      "medium_frequency_jitter": 1800,  # 30 minutes
      "low_frequency_base": 86400,      # 24 hours
      "low_frequency_jitter": 3600,     # 1 hour
      "static_base": 604800,            # 1 week
      "static_jitter": 43200             # 12 hours
    }
  }
}
```

## Advanced Features Configuration

### Deduplication System
```json
{
  "deduplication": {
    "enabled": true,
    "similarity_threshold": 0.90,
    "min_importance_diff": 0.05,
    "preserve_high_access": true,
    "collections": ["short_term", "long_term"],
    "advanced_features": {
      "domain_awareness": {
        "enabled": true,
        "domain_thresholds": {
          "code": 0.95,
          "text": 0.85,
          "data": 0.90,
          "documentation": 0.80
        }
      },
      "semantic_clustering": {
        "enabled": true,
        "max_clusters": 10,
        "min_cluster_size": 2
      },
      "enable_auto_optimization": true
    }
  }
}
```

### Analytics Configuration
```json
{
  "analytics": {
    "enabled": true,
    "intelligence_system": {
      "enabled": true,
      "analysis_depth": "basic",
      "roi_scoring_enabled": true
    },
    "performance_monitoring": {
      "track_generation_time": true,
      "track_resource_usage": false
    }
  }
}
```

### Chunk Relationships
```json
{
  "chunk_relationships": {
    "enabled": true,
    "context_window_size": 2,
    "track_deduplication_history": true,
    "preserve_document_structure": true
  }
}
```

## Domain Pattern Configuration

### Pattern Structure
```json
{
  "memory_scoring": {
    "domain_patterns": {
      "case_sensitive": false,
      "patterns": {
        "high_value_content": {
          "keywords": ["important", "critical", "urgent"],
          "bonus": 0.3,
          "match_mode": "any"
        },
        "technical_content": {
          "keywords": ["function", "error", "implementation"],
          "bonus": 0.2,
          "match_mode": "any"
        }
      }
    }
  }
}
```

### Permanence Triggers
```json
{
  "memory_scoring": {
    "domain_patterns": {
      "permanence_triggers": {
        "critical_information": {
          "keywords": ["critical", "permanent", "must remember"],
          "boost": 0.25
        }
      }
    }
  }
}
```

## Environment-Specific Configuration

### Development Environment
```json
{
  "logging": {
    "level": "DEBUG",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "logs/mcp_server.log"
  },
  "lifecycle": {
    "maintenance": {
      "cleanup_interval_hours": 1,
      "deep_maintenance_interval_hours": 6
    }
  }
}
```

### Production Environment
```json
{
  "logging": {
    "level": "INFO",
    "format": "%(asctime)s - %(levelname)s - %(message)s",
    "file": "/var/log/mcp-server/server.log"
  },
  "lifecycle": {
    "maintenance": {
      "cleanup_interval_hours": 6,
      "deep_maintenance_interval_hours": 24
    }
  }
}
```

## Configuration Validation

### Using the Configuration Wizard
```bash
# Interactive configuration
python scripts/config_wizard.py

# Template-based setup
python scripts/config_wizard.py template

# Validation only
python scripts/validate_config.py
```

### Manual Validation
```bash
# Test configuration loading
python -c "
from src.mcp_memory_server.config import Config
config = Config('config.json')
print('Configuration loaded successfully')
print(f'Server will run on {config.get_server_config()[\"host\"]}:{config.get_server_config()[\"port\"]}')
"
```

## Performance Tuning

### Memory Usage Optimization
```json
{
  "memory_management": {
    "short_term_max_size": 25        # Reduce for lower memory
  },
  "lifecycle": {
    "maintenance": {
      "cleanup_interval_hours": 2,    # More frequent cleanup
      "statistics_interval_hours": 6
    }
  }
}
```

### Query Performance Optimization
```json
{
  "embeddings": {
    "chunk_size": 500,               # Smaller chunks for faster processing
    "chunk_overlap": 50
  },
  "analytics": {
    "caching": {
      "enabled": true,
      "cache_duration_minutes": 15,
      "max_cache_size": 100
    }
  }
}
```

## Troubleshooting

### Common Issues

#### Server Won't Start
1. **Check Configuration Syntax**:
   ```bash
   python -m json.tool config.json
   ```

2. **Validate Paths**:
   ```bash
   python scripts/validate_config.py
   ```

3. **Check Port Availability**:
   ```bash
   netstat -an | grep 8080
   ```

#### Memory Issues
1. **Reduce Memory Usage**:
   - Decrease `short_term_max_size`
   - Increase cleanup frequency
   - Enable more aggressive TTL settings

2. **Monitor Memory Usage**:
   ```bash
   # Check memory statistics via MCP tools
   # Use get_memory_stats tool
   ```

#### Slow Performance
1. **Enable Analytics**:
   ```json
   {
     "analytics": {
       "performance_monitoring": {
         "track_generation_time": true
       }
     }
   }
   ```

2. **Optimize Embeddings**:
   - Use smaller embedding models for faster processing
   - Reduce chunk sizes
   - Enable caching

### Debug Mode
```json
{
  "logging": {
    "level": "DEBUG"
  },
  "analytics": {
    "performance_monitoring": {
      "track_generation_time": true,
      "track_resource_usage": true
    }
  }
}
```

## Configuration Examples

### Minimal Configuration
```json
{
  "server": {"host": "127.0.0.1", "port": 8080},
  "database": {"persist_directory": "./data"},
  "embeddings": {"model_name": "sentence-transformers/all-MiniLM-L6-v2"}
}
```

### High-Performance Configuration
```json
{
  "memory_management": {
    "short_term_max_size": 200
  },
  "deduplication": {"enabled": true},
  "analytics": {
    "enabled": true,
    "caching": {"enabled": true}
  }
}
```

### Resource-Constrained Configuration
```json
{
  "memory_management": {
    "short_term_max_size": 10
  },
  "lifecycle": {
    "maintenance": {
      "cleanup_interval_hours": 1
    }
  },
  "deduplication": {"enabled": false}
}
```

## Security Considerations

### Network Security
- Bind to `127.0.0.1` for local-only access
- Use appropriate firewall rules for network access
- Consider reverse proxy for production deployments

### Data Privacy
- Configure appropriate log levels to avoid sensitive data in logs
- Use secure storage paths with appropriate permissions
- Regular cleanup of expired data

### Access Control
- Implement client authentication if exposing over network
- Use environment variables for sensitive configuration
- Restrict file system permissions on configuration files

---

For more detailed configuration examples, see the `config/domains/` directory for domain-specific configurations.