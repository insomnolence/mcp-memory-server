# MCP Memory Server - Domain Configuration Guide

## 🎯 Overview

The MCP Memory Server supports **domain-specific configuration** - you can configure it for ANY domain by defining keywords and patterns. No code changes required!

The system uses a **pattern engine** that scores content based on **your custom keywords** and **weights**. Simply define what's important in your domain and the system adapts automatically.

## 🚀 Quick Start

### Select Existing Domain
```bash
# Use business domain
MCP_DOMAIN=business-development python3 scripts/start_server.py

# Use research domain  
MCP_DOMAIN=research python3 scripts/start_server.py

# Use creative writing domain
MCP_DOMAIN=creative-writing python3 scripts/start_server.py
```

### Available Domains
- `software-development` (default) - Code, bugs, solutions, architecture
- `business-development` - Revenue, deals, KPIs, market intelligence
- `research` - Academic research, methodology, findings, evidence
- `creative-writing` - Characters, plot, dialogue, world-building
- `cooking` - Recipes, techniques, ingredients, innovations
- `personal` - General personal knowledge and conversations

## 🔧 Domain Configuration Structure

### Basic Pattern Definition
```json
{
  "memory_scoring": {
    "domain_patterns": {
      "case_sensitive": false,
      "patterns": {
        "pattern_name": {
          "keywords": ["important", "keywords", "for", "scoring"],
          "bonus": 0.4,
          "match_mode": "any"
        }
      },
      "permanence_triggers": {
        "critical_content": {
          "keywords": ["breakthrough", "must remember"],
          "boost": 0.25
        }
      }
    }
  }
}
```

### Configuration Options

#### Pattern Settings
- **`keywords`**: List of words/phrases to detect (required)
- **`bonus`**: Score boost (0.0-1.0) when pattern matches (required)
- **`match_mode`**: How to match keywords (optional, default: "any")
  - `"any"` - Any keyword matches (recommended)
  - `"all"` - All keywords must be present
  - `"weighted"` - Different weights per keyword

#### Global Settings
- **`case_sensitive`**: Enable case-sensitive matching (default: false)

#### Advanced Options
```json
{
  "patterns": {
    "advanced_pattern": {
      "keywords": ["basic", "keywords"],
      "regex_patterns": ["\\$[0-9,]+", "\\d+%"],  // Optional regex
      "bonus": 0.4,
      "weight_distribution": {  // For weighted mode
        "critical": 0.6,
        "important": 0.4
      }
    }
  }
}
```

## 📋 Domain Examples

### Business Development
**File**: `config/domains/business-development.json`

```json
{
  "memory_scoring": {
    "domain_patterns": {
      "case_sensitive": false,
      "patterns": {
        "revenue_opportunities": {
          "keywords": [
            "revenue", "profit", "deal", "contract", "sale", 
            "ROI", "KPI", "quarterly", "growth", "target"
          ],
          "bonus": 0.4,
          "match_mode": "any"
        },
        "market_intelligence": {
          "keywords": [
            "competitor", "market share", "industry trend", 
            "analysis", "positioning", "strategy"
          ],
          "bonus": 0.35,
          "match_mode": "any"
        },
        "client_relationship": {
          "keywords": [
            "client", "customer", "stakeholder", "partnership", 
            "relationship", "satisfaction", "feedback"
          ],
          "bonus": 0.3,
          "match_mode": "any"
        }
      },
      "permanence_triggers": {
        "critical_business": {
          "keywords": [
            "major deal", "strategic partnership", "acquisition", 
            "merger", "IPO", "funding round"
          ],
          "boost": 0.3
        },
        "executive_decisions": {
          "keywords": [
            "board decision", "CEO announcement", "strategic pivot", 
            "company direction", "policy change"
          ],
          "boost": 0.25
        }
      }
    }
  }
}
```

**Result Examples:**
- "Closed $2M deal with enterprise client" → Score: 1.000 → **Permanent**
- "Quarterly revenue meeting notes" → Score: 0.400 → **Long-term**
- "Competitive analysis report" → Score: 0.750 → **Long-term**

### Scientific Research
**File**: `config/domains/research.json`

```json
{
  "memory_scoring": {
    "domain_patterns": {
      "case_sensitive": false,
      "patterns": {
        "research_findings": {
          "keywords": [
            "discovered", "evidence", "result", "conclusion", 
            "significant", "correlation", "causation", "proof"
          ],
          "bonus": 0.45,
          "match_mode": "any"
        },
        "methodology": {
          "keywords": [
            "methodology", "protocol", "procedure", "approach", 
            "design", "sample", "control", "experimental"
          ],
          "bonus": 0.35,
          "match_mode": "any"
        },
        "statistical_analysis": {
          "keywords": [
            "statistical", "p-value", "hypothesis", "regression", 
            "correlation", "variance", "confidence interval"
          ],
          "bonus": 0.4,
          "match_mode": "any"
        },
        "literature_review": {
          "keywords": [
            "literature", "citation", "reference", "study", 
            "paper", "journal", "publication"
          ],
          "bonus": 0.25,
          "match_mode": "any"
        }
      },
      "permanence_triggers": {
        "breakthrough": {
          "keywords": [
            "breakthrough", "groundbreaking", "novel discovery", 
            "paradigm shift", "revolutionary"
          ],
          "boost": 0.4
        },
        "validated_results": {
          "keywords": [
            "peer reviewed", "published", "validated", 
            "replicated", "confirmed"
          ],
          "boost": 0.3
        }
      }
    }
  }
}
```

**Result Examples:**
- "Groundbreaking discovery with statistical significance" → Score: 1.000 → **Permanent**
- "Experimental methodology for data collection" → Score: 0.350 → **Short-term**
- "Literature review findings" → Score: 0.250 → **Short-term**

### Creative Writing
**File**: `config/domains/creative-writing.json`

```json
{
  "memory_scoring": {
    "domain_patterns": {
      "case_sensitive": false,
      "patterns": {
        "character_development": {
          "keywords": [
            "character", "protagonist", "antagonist", "motivation", 
            "backstory", "personality", "development", "arc"
          ],
          "bonus": 0.4,
          "match_mode": "any"
        },
        "plot_elements": {
          "keywords": [
            "plot", "story", "narrative", "twist", "climax", 
            "conflict", "resolution", "tension"
          ],
          "bonus": 0.35,
          "match_mode": "any"
        },
        "world_building": {
          "keywords": [
            "world", "setting", "environment", "culture", 
            "society", "rules", "magic system", "technology"
          ],
          "bonus": 0.35,
          "match_mode": "any"
        },
        "dialogue_craft": {
          "keywords": [
            "dialogue", "conversation", "voice", "tone", 
            "speech pattern", "accent", "vernacular"
          ],
          "bonus": 0.3,
          "match_mode": "any"
        }
      },
      "permanence_triggers": {
        "story_breakthrough": {
          "keywords": [
            "major plot point", "story breakthrough", 
            "character revelation", "perfect scene"
          ],
          "boost": 0.3
        },
        "creative_breakthrough": {
          "keywords": [
            "creative breakthrough", "inspired idea", 
            "perfect dialogue", "amazing concept"
          ],
          "boost": 0.25
        }
      }
    }
  }
}
```

### Cooking & Culinary Arts
**File**: `config/domains/cooking.json`

```json
{
  "memory_scoring": {
    "domain_patterns": {
      "case_sensitive": false,
      "patterns": {
        "recipe_innovation": {
          "keywords": [
            "recipe", "dish", "creation", "innovation", 
            "technique", "method", "preparation", "cooking"
          ],
          "bonus": 0.4,
          "match_mode": "any"
        },
        "ingredient_knowledge": {
          "keywords": [
            "ingredient", "flavor", "seasoning", "spice", 
            "herb", "combination", "pairing", "substitution"
          ],
          "bonus": 0.35,
          "match_mode": "any"
        },
        "culinary_technique": {
          "keywords": [
            "technique", "method", "temperature", "timing", 
            "texture", "consistency", "doneness", "skill"
          ],
          "bonus": 0.3,
          "match_mode": "any"
        }
      },
      "permanence_triggers": {
        "signature_creation": {
          "keywords": [
            "signature dish", "perfect recipe", 
            "culinary breakthrough", "restaurant quality"
          ],
          "boost": 0.3
        }
      }
    }
  }
}
```

## 🛠️ Creating Custom Domains

### Step 1: Identify Your Domain
Think about your specific use case:
- What type of content will you store?
- What keywords indicate importance?
- What should trigger permanent storage?

### Step 2: Create Domain File
```bash
# Create new domain configuration
cp config/domains/software-development.json config/domains/your-domain.json
```

### Step 3: Define Patterns
Edit your domain file with relevant keywords:

```json
{
  "memory_scoring": {
    "domain_patterns": {
      "patterns": {
        "domain_priority_1": {
          "keywords": ["keyword1", "keyword2", "keyword3"],
          "bonus": 0.4
        },
        "domain_priority_2": {
          "keywords": ["keyword4", "keyword5"],
          "bonus": 0.3
        }
      },
      "permanence_triggers": {
        "critical_content": {
          "keywords": ["critical", "important", "breakthrough"],
          "boost": 0.25
        }
      }
    }
  }
}
```

### Step 4: Test Your Domain
```bash
# Test with your new domain
MCP_DOMAIN=your-domain python3 scripts/start_server.py
```

## 📊 Scoring Examples

### How Scoring Works
```
Base Content Score (0.0 - 0.5)
    + Pattern Bonus (0.0 - 0.5)
    + Context Bonuses (solution, important flags)
    + Permanence Boost (if triggered)
    = Final Importance Score (0.0 - 1.0+)
```

### Scoring Scenarios

#### Business Domain
- **"Quarterly revenue increased 25%"**
  - Base: 0.2 + Revenue pattern (0.4) = **0.6** → Short-term
  
- **"Major deal with Fortune 500 client signed"**
  - Base: 0.2 + Revenue (0.4) + Major deal trigger (0.3) = **0.9** → Long-term
  
- **"Strategic acquisition approved by board"**
  - Base: 0.2 + Business (0.35) + Critical trigger (0.3) = **0.85** → Long-term

#### Research Domain
- **"Literature review on ML algorithms"**
  - Base: 0.15 + Literature (0.25) = **0.4** → Short-term
  
- **"Significant correlation found (p<0.01)"**
  - Base: 0.2 + Findings (0.45) + Statistical (0.4) = **1.05** → **Permanent**
  
- **"Breakthrough discovery published in Nature"**
  - Base: 0.2 + Findings (0.45) + Breakthrough trigger (0.4) = **1.05** → **Permanent**

## ⚙️ Advanced Configuration

### Multi-Domain Patterns
```json
{
  "patterns": {
    "cross_domain": {
      "keywords": ["innovation", "breakthrough", "discovery"],
      "bonus": 0.3,
      "match_mode": "any"
    },
    "domain_specific": {
      "keywords": ["technical", "analysis", "implementation"],
      "bonus": 0.25,
      "match_mode": "any"
    }
  }
}
```

### Regex Pattern Support
```json
{
  "patterns": {
    "financial_data": {
      "keywords": ["revenue", "profit"],
      "regex_patterns": [
        "\\$[0-9,]+",           // Dollar amounts
        "\\d+%",                // Percentages
        "Q[1-4]\\s+\\d{4}"      // Quarters (Q1 2024)
      ],
      "bonus": 0.4
    }
  }
}
```

### Weighted Keywords
```json
{
  "patterns": {
    "weighted_importance": {
      "keywords": ["critical", "important", "moderate"],
      "match_mode": "weighted",
      "weight_distribution": {
        "critical": 0.6,
        "important": 0.3,
        "moderate": 0.1
      },
      "bonus": 0.4
    }
  }
}
```

## 🚀 Domain Templates

### Academic Research Template
```bash
# Copy and customize
cp config/domains/research.json config/domains/my-research.json
```

### Business Intelligence Template
```bash
# Copy and customize
cp config/domains/business-development.json config/domains/my-business.json
```

### Personal Knowledge Template
```json
{
  "memory_scoring": {
    "domain_patterns": {
      "patterns": {
        "personal_insights": {
          "keywords": ["learned", "realized", "insight", "idea"],
          "bonus": 0.3
        },
        "important_decisions": {
          "keywords": ["decision", "choice", "conclusion"],
          "bonus": 0.35
        }
      }
    }
  }
}
```

## 🔧 Best Practices

### Keyword Selection
1. **Be Specific** - Use domain-specific terminology
2. **Include Synonyms** - Cover different ways to express concepts
3. **Add Action Words** - "discovered", "achieved", "breakthrough"
4. **Consider Emotional Indicators** - "excited", "concerned", "critical"

### Bonus Scoring
- **0.5+**: Extremely important content (rare)
- **0.4**: Very important domain content
- **0.3**: Important domain content
- **0.2**: Moderately important
- **0.1**: Slight importance boost

### Testing Your Domain
```bash
# Test scoring with sample content
echo "Your test content here" | python3 scripts/test_domain_scoring.py --domain your-domain
```

### Domain Maintenance
1. **Monitor Results** - Check what gets scored highly
2. **Adjust Thresholds** - Fine-tune bonuses based on results
3. **Add Patterns** - Expand keywords based on usage
4. **Review Permanence** - Ensure critical content is preserved

## 🎯 Domain Switching

### Multiple Domains
```bash
# Start different servers for different domains
MCP_DOMAIN=business-development python3 scripts/start_server.py &
MCP_DOMAIN=research python3 scripts/start_server.py &
```

### Client Configuration
```json
{
  "mcpServers": {
    "memory-business": {
      "command": "python3",
      "args": ["scripts/start_server.py"],
      "env": {"MCP_DOMAIN": "business-development"}
    },
    "memory-research": {
      "command": "python3", 
      "args": ["scripts/start_server.py"],
      "env": {"MCP_DOMAIN": "research"}
    }
  }
}
```

## 📈 Performance Considerations

### Keyword Optimization
- **Avoid Too Many Keywords** - Start with 5-10 per pattern
- **Use Specific Terms** - "quarterly revenue" vs "money"  
- **Test Pattern Performance** - Monitor scoring accuracy

### Memory Usage
- **Pattern Complexity** - Simple patterns are faster
- **Regex Usage** - Use sparingly for performance
- **Keyword Count** - More keywords = more processing

The domain configuration system is designed to be **flexible** and **extensible**. Start with existing examples and customize based on your specific needs and usage patterns.