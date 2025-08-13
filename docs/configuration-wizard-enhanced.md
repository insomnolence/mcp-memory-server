# Configuration Wizard Guide

The MCP Memory Server Configuration Wizard provides an interactive solution for configuring your memory server through user-friendly questions instead of editing complex technical parameters.

## Overview

### What Was Built

The wizard system integrates the sophisticated modular architecture from `scripts/wizard/` with comprehensive configuration coverage, creating a unified professional configuration experience.

**Key Components:**
- **`scripts/config_wizard.py`**: Main unified wizard with professional UI
- **`scripts/wizard/ui.py`**: Professional styling and interface components  
- **`scripts/wizard/questions.py`**: Enhanced question flow with server and domain configuration
- **`scripts/wizard/mappers.py`**: Extended mapping system for all configuration aspects
- **`scripts/wizard/validators.py`**: Comprehensive validation and preview system
- **`scripts/wizard/templates.py`**: Pre-built configuration templates

## Features

### 🎨 Professional User Interface
- **ANSI Color Support**: Automatic terminal color detection
- **Progress Indicators**: Visual progress bars and completion tracking
- **Clear Formatting**: Section headers, bullet points, and consistent styling
- **Error Handling**: Graceful error recovery with helpful messages
- **Confirmation Dialogs**: Professional confirmation and backup handling

### 🔧 Comprehensive Configuration Coverage

#### Memory Strategy Configuration
- **Retention Periods**: From session-based (8 hours) to permanent storage
- **Importance Weighting**: Semantic relevance, recency, frequency, and explicit importance
- **Content Prioritization**: Code, errors, architecture, critical content, documentation
- **Performance Trade-offs**: Performance vs accuracy preferences

#### Server Configuration  
- **Host Binding**: Localhost, network accessible, or custom host addresses
- **Port Selection**: Validated port selection with conflict checking
- **Server Identity**: Custom titles and descriptions for client identification
- **Protocol Management**: Version and compatibility settings

#### Domain Customization
- **Technology Keywords**: Programming languages, frameworks, tools, methodologies
- **Business Terminology**: Processes, metrics, customer terms, industry jargon  
- **Research Patterns**: Academic concepts, statistical terms, research methods
- **Creative Work**: Design principles, artistic terms, creative processes
- **Custom Categories**: User-defined keyword patterns with bonus scoring

#### Advanced Options
- **Custom Thresholds**: Fine-tune importance cutoffs for long-term storage
- **Consolidation Frequency**: Optimize memory organization intervals
- **TTL Management**: Time-to-live settings for different content types
- **Logging Configuration**: Log levels, formats, and output destinations

### 🛠️ Template System
Pre-built templates provide instant configuration for common scenarios:

- **Development**: Optimized for software development with code and debugging focus
- **Research**: Extended retention for research findings and documentation
- **Creative**: Balanced settings for writing, brainstorming, and creative projects
- **Business**: Meeting notes, processes, and customer interaction optimization
- **Minimal**: Resource-efficient with aggressive cleanup for limited systems
- **Maximum**: Extensive retention with minimal cleanup for abundant resources

### 🔍 Validation & Preview
- **Real-time Validation**: Comprehensive configuration validation with clear error messages
- **Impact Previews**: Human-readable explanations of configuration choices
- **Scenario Examples**: Concrete examples showing how settings affect behavior
- **Technical Summaries**: Key parameters displayed clearly before saving

## Usage

### Quick Template Setup (30 seconds)
```bash
python3 scripts/config_wizard.py template
```
Select from 6 pre-optimized templates for instant configuration.

### Full Interactive Wizard (5-10 minutes)  
```bash
python3 scripts/config_wizard.py
```
Complete configuration through guided questions covering all aspects.

### Help & Information
```bash
python3 scripts/config_wizard.py --help
python3 scripts/wizard_demo.py  # Feature demonstration
```

## Architecture Integration

### Modular Design
The wizard leverages a clean modular architecture:

```
scripts/wizard/
├── ui.py           # Professional interface components
├── questions.py    # Question definitions and flow logic
├── mappers.py      # Answer-to-configuration translation
├── validators.py   # Validation and preview generation  
└── templates.py    # Pre-built configuration templates
```

### Dependency Management
Questions are conditionally displayed based on previous answers:
- Template selection skips detailed configuration
- Server configuration appears only in custom mode
- Domain customization is optional with category-specific keyword collection
- Advanced settings are clearly separated for power users

### Configuration Generation
The mapping system translates human answers to technical parameters:
- **Use Case Optimization**: Adjusts defaults based on primary use case
- **Smart Defaults**: Professionally tuned settings for each scenario  
- **Custom Integration**: Seamlessly integrates user customizations
- **Template Merging**: Combines template settings with custom overrides

## Professional Features

### User Experience
- **Progress Tracking**: Clear indication of wizard progress and remaining steps
- **Help System**: Contextual help and impact explanations for each choice
- **Error Recovery**: Graceful handling of invalid inputs with retry prompts
- **Confirmation Flow**: Preview and confirmation before saving changes

### Configuration Management  
- **Automatic Backup**: Existing configurations are safely backed up
- **Directory Creation**: Required directories are created automatically  
- **Validation Pipeline**: Multi-stage validation ensures configuration correctness
- **Format Consistency**: Professional JSON formatting with sorted keys

### Extensibility
- **Modular Questions**: Easy to add new configuration areas
- **Template System**: Simple to create new pre-built configurations
- **Validation Framework**: Extensible validation rules and checks
- **UI Components**: Reusable interface elements for consistency

## Implementation Examples

### Adding New Configuration Areas
```python
# In questions.py
Question(
    id="new_feature",
    title="Configure new feature?", 
    description="This enables the new feature with optimized defaults.",
    question_type=QuestionType.BOOLEAN,
    default=False
)

# In mappers.py  
def _apply_new_feature_mapping(self, config: Dict[str, Any], answers: Dict[str, Any]):
    if answers.get("new_feature"):
        config["new_feature"] = {"enabled": True}
```

### Creating Custom Templates
```python
# In templates.py
@staticmethod
def _custom_template() -> Dict[str, Any]:
    return {
        "memory_scoring": {
            "importance_threshold": 0.8,  # Custom threshold
            "scoring_weights": {"semantic": 0.6, "recency": 0.4}
        }
    }
```

## Migration from Simple Wizard

The enhanced wizard replaces `scripts/setup_wizard.py` with significant improvements:

**Enhanced Capabilities:**
- Server configuration (host, port, title)  
- Domain pattern customization
- Template-based quick setup
- Professional UI with colors and progress
- Comprehensive validation and previews
- Backup handling and error recovery

**Maintained Compatibility:**
- Same configuration file format (`config.json`)
- Compatible with existing validation tools
- Preserves all existing configuration options

## Next Steps

1. **Try the wizard**: `python3 scripts/config_wizard.py template`
2. **Explore features**: `python3 scripts/wizard_demo.py`
3. **Validate configuration**: `python3 scripts/validate_config.py`
4. **Start server**: `python3 scripts/start_server.py`

The enhanced wizard provides a complete, professional configuration solution that makes MCP Memory Server setup accessible to all users while maintaining the power and flexibility needed for advanced configurations.