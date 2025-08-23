# MCP Memory Server - Domain Configuration Guide

## Overview

The MCP Memory Server supports domain-specific configuration - you can configure it for any domain by defining keywords and patterns. No code changes required.

The system uses a pattern engine that scores content based on your custom keywords and weights. Simply define what's important in your domain and the system adapts automatically.

## Quick Start

### Select Existing Domain
```bash
# Use business domain
MCP_DOMAIN=business-development python scripts/start_server.py

# Use research domain  
MCP_DOMAIN=research python scripts/start_server.py

# Use creative writing domain
MCP_DOMAIN=creative-writing python scripts/start_server.py

# Use cooking domain
MCP_DOMAIN=cooking python scripts/start_server.py
```

### Available Pre-built Domains
- **business-development** - Revenue, KPIs, meetings, deals, market intelligence
- **research** - Academic research, methodology, findings, evidence, publications
- **creative-writing** - Characters, plot, dialogue, world-building, narrative
- **cooking** - Recipes, techniques, ingredients, flavors, culinary innovations

## Creating Custom Domains

### Domain File Structure
Create a new file in `config/domains/your-domain.json`:

```json
{
  "memory_scoring": {
    "domain_patterns": {
      "case_sensitive": false,
      "patterns": {
        "high_value_content": {
          "keywords": ["critical", "important", "urgent", "priority"],
          "bonus": 0.3,
          "match_mode": "any"
        },
        "domain_specific": {
          "keywords": ["domain", "specific", "keywords"],
          "bonus": 0.25,
          "match_mode": "any"
        }
      },
      "permanence_triggers": {
        "must_remember": {
          "keywords": ["permanent", "remember", "critical"],
          "boost": 0.4
        }
      }
    }
  }
}
```

### Pattern Configuration Parameters

#### Keywords Array
```json
"keywords": ["word1", "word2", "phrase with spaces"]
```
- Case-insensitive by default
- Supports multi-word phrases
- Matches partial words (e.g., "code" matches "coding")

#### Bonus Values
```json
"bonus": 0.3  # Adds 30% to importance score
```
- Range: 0.0 to 1.0
- Higher values = more important content
- Typical ranges:
  - Critical content: 0.3-0.5
  - Important content: 0.2-0.3
  - Relevant content: 0.1-0.2

#### Match Modes
```json
"match_mode": "any"    # Match any keyword (default)
"match_mode": "all"    # Match all keywords
"match_mode": "weighted"  # Weighted scoring
```

## Domain Examples

### Software Development
```json
{
  "memory_scoring": {
    "domain_patterns": {
      "patterns": {
        "critical_bugs": {
          "keywords": ["bug", "error", "crash", "exception", "failed"],
          "bonus": 0.4,
          "match_mode": "any"
        },
        "code_solutions": {
          "keywords": ["solution", "fix", "implement", "function", "class"],
          "bonus": 0.3,
          "match_mode": "any"
        },
        "architecture": {
          "keywords": ["design", "architecture", "pattern", "structure"],
          "bonus": 0.25,
          "match_mode": "any"
        }
      },
      "permanence_triggers": {
        "production_issues": {
          "keywords": ["production", "critical bug", "security"],
          "boost": 0.5
        }
      }
    }
  }
}
```

### Medical/Healthcare
```json
{
  "memory_scoring": {
    "domain_patterns": {
      "patterns": {
        "patient_critical": {
          "keywords": ["urgent", "critical", "emergency", "stat"],
          "bonus": 0.5,
          "match_mode": "any"
        },
        "diagnoses": {
          "keywords": ["diagnosis", "symptom", "treatment", "medication"],
          "bonus": 0.35,
          "match_mode": "any"
        },
        "procedures": {
          "keywords": ["procedure", "surgery", "protocol", "guideline"],
          "bonus": 0.3,
          "match_mode": "any"
        }
      },
      "permanence_triggers": {
        "patient_safety": {
          "keywords": ["allergy", "adverse reaction", "contraindication"],
          "boost": 0.6
        }
      }
    }
  }
}
```

### Legal
```json
{
  "memory_scoring": {
    "domain_patterns": {
      "patterns": {
        "case_critical": {
          "keywords": ["deadline", "court date", "filing", "statute"],
          "bonus": 0.4,
          "match_mode": "any"
        },
        "legal_research": {
          "keywords": ["precedent", "case law", "ruling", "statute"],
          "bonus": 0.35,
          "match_mode": "any"
        },
        "client_matters": {
          "keywords": ["client", "agreement", "contract", "negotiation"],
          "bonus": 0.3,
          "match_mode": "any"
        }
      }
    }
  }
}
```

### Education/Academic
```json
{
  "memory_scoring": {
    "domain_patterns": {
      "patterns": {
        "research_findings": {
          "keywords": ["research", "study", "findings", "data", "results"],
          "bonus": 0.35,
          "match_mode": "any"
        },
        "methodology": {
          "keywords": ["method", "approach", "technique", "protocol"],
          "bonus": 0.3,
          "match_mode": "any"
        },
        "citations": {
          "keywords": ["citation", "reference", "source", "bibliography"],
          "bonus": 0.25,
          "match_mode": "any"
        }
      }
    }
  }
}
```

## Advanced Pattern Features

### Weighted Keywords
```json
{
  "weighted_content": {
    "keywords": {
      "critical": 0.4,
      "important": 0.3,
      "relevant": 0.2,
      "useful": 0.1
    },
    "match_mode": "weighted"
  }
}
```

### Phrase Matching
```json
{
  "specific_phrases": {
    "keywords": [
      "machine learning model",
      "data preprocessing",
      "feature engineering",
      "model evaluation"
    ],
    "bonus": 0.35,
    "match_mode": "any"
  }
}
```

### Context-Aware Patterns
```json
{
  "context_patterns": {
    "meeting_action_items": {
      "keywords": ["action item", "todo", "follow up", "assign"],
      "bonus": 0.4,
      "context": "meeting"
    },
    "code_reviews": {
      "keywords": ["review", "comment", "suggestion", "improvement"],
      "bonus": 0.3,
      "context": "code"
    }
  }
}
```

## Testing Domain Configuration

### Configuration Validation
```bash
# Test your domain configuration
python scripts/validate_config.py config/domains/your-domain.json

# Start server with your domain
MCP_DOMAIN=your-domain python scripts/start_server.py
```

### Testing Pattern Matching
```python
# Test patterns with sample content
from src.mcp_memory_server.memory.scorer import DomainPatternEngine

engine = DomainPatternEngine(your_domain_config)
score = engine.analyze_content("Your test content here")
print(f"Domain bonus: {score}")
```

## Domain Configuration Best Practices

### Keyword Selection
1. **Be Specific**: Use domain-specific terminology
2. **Include Variations**: Consider synonyms and related terms
3. **Test Thoroughly**: Validate with real content from your domain
4. **Iterative Refinement**: Adjust based on real usage patterns

### Scoring Strategy
1. **Balanced Bonuses**: Avoid over-weighting any single pattern
2. **Hierarchical Importance**: Use different bonus levels for different priority content
3. **Permanence Triggers**: Identify truly critical information that should never expire

### Performance Considerations
1. **Keyword Count**: Keep keyword lists manageable (10-50 keywords per pattern)
2. **Pattern Count**: Limit to 5-10 patterns per domain for optimal performance
3. **Regular Review**: Periodically assess pattern effectiveness

## Integration with Memory System

### How Domain Patterns Work
1. **Content Analysis**: Each document is analyzed against all patterns
2. **Score Calculation**: Matching keywords add bonus points to importance score
3. **Tier Assignment**: Enhanced scores influence memory tier placement
4. **Permanence Evaluation**: Permanence triggers can force documents to permanent storage

### Memory Tier Impact
- **Short-term**: Base importance + small domain bonus
- **Long-term**: Base importance + medium domain bonus (≥ 0.7 total)
- **Permanent**: Base importance + high domain bonus (≥ 0.95 total) or permanence trigger

## Troubleshooting Domain Configuration

### Common Issues

#### Patterns Not Matching
1. **Check Case Sensitivity**: Ensure `case_sensitive` setting is correct
2. **Verify Keywords**: Test with simple, exact keyword matches first
3. **Debug Mode**: Enable debug logging to see pattern matching results

#### Unexpected Scoring
1. **Review Bonus Values**: Ensure bonuses are in reasonable ranges (0.1-0.5)
2. **Check Pattern Overlap**: Multiple patterns can stack bonuses
3. **Monitor Pattern Effectiveness**: Use analytics tools to assess impact

#### Performance Issues
1. **Reduce Pattern Complexity**: Simplify keyword lists and patterns
2. **Optimize Matching**: Use specific rather than broad keywords
3. **Profile Performance**: Monitor system performance with domain patterns enabled

### Debug Configuration
```json
{
  "logging": {
    "level": "DEBUG"
  },
  "memory_scoring": {
    "debug_scoring": true,
    "domain_patterns": {
      "debug_matching": true
    }
  }
}
```

## Migration and Updates

### Updating Existing Domains
1. **Backup Current Configuration**: Always backup before changes
2. **Test Changes**: Validate new patterns before deployment
3. **Gradual Rollout**: Consider phased updates for production systems

### Domain Evolution
- Monitor domain effectiveness over time
- Adjust patterns based on usage analytics
- Add new patterns as domain needs evolve
- Remove ineffective patterns to improve performance

---

Domain configuration makes the MCP Memory Server adaptable to any field or use case. The pattern system provides powerful content analysis while remaining simple to configure and maintain.