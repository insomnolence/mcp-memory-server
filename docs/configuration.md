# MCP Memory Server - Configuration Guide

## 🚀 Quick Start

The MCP Memory Server uses a single configuration file (`config.json`) with optional domain-specific overrides for different use cases.

### Simple Setup
```bash
# Use default configuration
python3 scripts/start_server.py

# Use domain-specific configuration
MCP_DOMAIN=business-development python3 scripts/start_server.py
```

### Available Domains
- `software-development` (default) - Code, bugs, solutions, architecture
- `business-development` - Revenue, deals, KPIs, market intelligence
- `research` - Academic research, methodology, findings, evidence
- `creative-writing` - Characters, plot, dialogue, world-building
- `cooking` - Recipes, techniques, ingredients, innovations
- `personal` - General personal knowledge and conversations

## 📁 Configuration Architecture

### Directory Structure
```
config/
├── domains/                    # Domain-specific configurations
│   ├── business-development.json
│   ├── research.json
│   ├── creative-writing.json
│   └── cooking.json
└── example.json               # Configuration template

config.json                    # Main configuration file
```

### How Configurations Merge
1. **Base Configuration**: `config.json` (complete configuration)
2. **Domain Overlay**: Domain config (e.g., `config/domains/business-development.json`) 
3. **Final Result**: Merged configuration with domain-specific patterns

## 🎯 Domain Configuration

### Domain Pattern System
Each domain defines important keywords and patterns for content scoring:

```json
{
  "memory_scoring": {
    "domain_patterns": {
      "case_sensitive": false,
      "patterns": {
        "domain_priority": {
          "keywords": ["important", "keywords", "for", "this", "domain"],
          "bonus": 0.4,
          "match_mode": "any"
        },
        "critical_content": {
          "keywords": ["critical", "urgent", "breaking"],
          "bonus": 0.5,
          "match_mode": "any"
        }
      },
      "permanence_triggers": {
        "high_importance": {
          "keywords": ["breakthrough", "must remember"],
          "boost": 0.25
        }
      }
    }
  }
}
```

### Domain Examples

#### Business Development (`config/domains/business-development.json`)
```json
{
  "memory_scoring": {
    "domain_patterns": {
      "patterns": {
        "revenue_opportunities": {
          "keywords": ["revenue", "profit", "deal", "contract", "sale", "ROI", "KPI"],
          "bonus": 0.4,
          "match_mode": "any"
        },
        "market_intelligence": {
          "keywords": ["competitor", "market share", "industry trend", "analysis"],
          "bonus": 0.35,
          "match_mode": "any"
        },
        "client_relationship": {
          "keywords": ["client", "customer", "stakeholder", "partnership"],
          "bonus": 0.3,
          "match_mode": "any"
        }
      },
      "permanence_triggers": {
        "critical_business": {
          "keywords": ["major deal", "strategic partnership", "acquisition"],
          "boost": 0.3
        }
      }
    }
  }
}
```

#### Research (`config/domains/research.json`)
```json
{
  "memory_scoring": {
    "domain_patterns": {
      "patterns": {
        "findings": {
          "keywords": ["discovered", "evidence", "result", "conclusion", "significant"],
          "bonus": 0.45,
          "match_mode": "any"
        },
        "methodology": {
          "keywords": ["methodology", "protocol", "procedure", "approach"],
          "bonus": 0.35,
          "match_mode": "any"
        },
        "data_analysis": {
          "keywords": ["statistical", "correlation", "p-value", "hypothesis"],
          "bonus": 0.4,
          "match_mode": "any"
        }
      },
      "permanence_triggers": {
        "breakthrough": {
          "keywords": ["breakthrough", "groundbreaking", "novel discovery"],
          "boost": 0.4
        }
      }
    }
  }
}
```

## 📊 Memory System Configuration

### Hierarchical Memory Tiers
```json
{
  "memory_scoring": {
    "importance_threshold": 0.7,
    "scoring_weights": {
      "semantic": 0.4,
      "recency": 0.3, 
      "frequency": 0.2,
      "importance": 0.1
    },
    "content_scoring": {
      "code_bonus": 0.3,
      "error_bonus": 0.2,
      "solution_bonus": 0.3,
      "important_bonus": 0.2,
      "language_bonus": 0.1
    }
  }
}
```

### TTL (Time-To-Live) System
```json
{
  "lifecycle": {
    "ttl": {
      "high_frequency_base": 300,      // 5 minutes
      "high_frequency_jitter": 60,     // ±1 minute
      "medium_frequency_base": 3600,   // 1 hour
      "medium_frequency_jitter": 600,  // ±10 minutes
      "low_frequency_base": 86400,     // 1 day
      "low_frequency_jitter": 7200,    // ±2 hours
      "static_base": 604800,           // 1 week
      "static_jitter": 86400           // ±1 day
    },
    "aging": {
      "enabled": true,
      "decay_rate": 0.1,
      "minimum_score": 0.1,
      "refresh_threshold_days": 7.0
    }
  }
}
```

### Permanence System
```json
{
  "memory_scoring": {
    "permanence_factors": {
      "architecture_decision": 0.2,
      "critical_bug_fix": 0.15,
      "core_documentation": 0.1,
      "user_explicit_permanent": 0.25,
      "system_configuration": 0.1
    }
  }
}
```

## 🔧 Advanced Configuration

### Custom Domain Creation
Create your own domain for any use case:

```json
{
  "memory_scoring": {
    "domain_patterns": {
      "patterns": {
        "astronomy_observations": {
          "keywords": ["telescope", "galaxy", "nebula", "observation", "discovery"],
          "bonus": 0.4,
          "match_mode": "any"
        },
        "celestial_events": {
          "keywords": ["eclipse", "transit", "conjunction", "meteor"],
          "bonus": 0.35,
          "match_mode": "any"
        }
      },
      "permanence_triggers": {
        "major_discovery": {
          "keywords": ["new planet", "breakthrough observation"],
          "boost": 0.3
        }
      }
    }
  }
}
```

### Background Maintenance
```json
{
  "lifecycle": {
    "maintenance": {
      "enabled": true,
      "cleanup_interval_hours": 1,
      "consolidation_interval_hours": 6,
      "statistics_interval_hours": 24,
      "deep_maintenance_interval_hours": 168
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
    "chunk_overlap": 100,
    "device": "auto"
  },
  "reranker": {
    "model_name": "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "enabled": true
  }
}
```

## 🚀 Usage Patterns

### Multiple Domain Setup
```bash
# Business server
MCP_DOMAIN=business-development python3 scripts/start_server.py &

# Research server (different port in domain config)
MCP_DOMAIN=research python3 scripts/start_server.py &
```

### Custom Configuration File
```bash
# Use specific config file
python3 scripts/start_server.py --config /path/to/custom/config.json
```

### Environment Variables
```bash
export MCP_DOMAIN=creative-writing
export MCP_DATA_PATH=/custom/data/location
python3 scripts/start_server.py
```

## 📋 Configuration Validation

### Validate Configuration
```bash
# Validate current config
python3 scripts/validate_config.py

# Validate specific file
python3 scripts/validate_config.py config/domains/business-development.json

# Validate with domain override
MCP_DOMAIN=research python3 scripts/validate_config.py
```

### Common Validation Errors
- Missing required sections
- Invalid scoring weight sums (must total 1.0)
- Invalid file paths
- Malformed JSON syntax
- Invalid port numbers
- Missing domain files

## 🔄 Migration Guide

### From Environment-Based Structure (Pre-Simplification)
If upgrading from the old environment-based structure:

1. **Use existing config.json:**
   - The system now uses a single `config.json` file
   - Environment complexity has been removed

2. **Update database paths:**
   ```json
   // Updated path (simplified)
   "persist_directory": "./data/memory"
   ```

3. **Test new structure:**
   ```bash
   python3 scripts/start_server.py
   ```

### From Hardcoded Values
All previous hardcoded defaults are preserved as fallbacks:
- No breaking changes to existing functionality
- Existing data remains accessible
- Configuration enhances but doesn't replace defaults

## 🛠️ Troubleshooting

### Server Won't Start
```bash
# Check configuration
python3 scripts/validate_config.py

# Test specific domain
MCP_DOMAIN=software-development python3 scripts/validate_config.py

# Check paths exist
ls -la data/memory/
```

### Domain Not Working
```bash
# Verify domain file exists
ls config/domains/your-domain.json

# Check domain merging
MCP_DOMAIN=your-domain python3 scripts/validate_config.py

# Review scoring patterns
cat config/domains/your-domain.json | grep -A10 "patterns"
```

### Performance Issues
1. **High memory usage**: Lower `short_term_max_size`
2. **Slow queries**: Adjust `chunk_size` and scoring thresholds
3. **TTL issues**: Review lifecycle configuration
4. **Pattern matching**: Optimize keyword lists in domain configs

### Connection Issues
```bash
# Check server status
curl http://127.0.0.1:8081/health

# Review server logs
tail -f mcp_server.log

# Test with debug logging
python3 scripts/start_server.py
```

## 📚 Best Practices

### Configuration Management
1. **Version control** your custom domain configurations
2. **Test configurations** before deployment
3. **Document custom patterns** for your team
4. **Monitor performance** after configuration changes
5. **Backup data** before major configuration updates

### Domain Design
1. **Use specific keywords** relevant to your domain
2. **Include action words** (achieved, discovered, critical)
3. **Test scoring** with sample content
4. **Iterate based on results** 
5. **Consider user mental models** when choosing keywords

### Performance Optimization
1. **Tune importance thresholds** based on your content volume
2. **Adjust TTL settings** for your retention needs
3. **Monitor memory usage** and adjust collection sizes
4. **Use appropriate chunk sizes** for your content types
5. **Enable maintenance** for long-running deployments

The configuration system is designed to be flexible and extensible. Start with the provided examples and customize based on your specific needs and usage patterns.