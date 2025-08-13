"""
Mappers to convert human-friendly answers to technical configuration parameters.

This module handles the translation between user choices and the actual
configuration values needed by the MCP Memory Server.
"""

from typing import Dict, Any, List
import math


class ConfigMapper:
    """Maps human answers to technical configuration parameters."""
    
    def __init__(self):
        self.base_config = self._get_base_config()
    
    def map_answers_to_config(self, answers: Dict[str, Any]) -> Dict[str, Any]:
        """Convert all answers to a complete configuration."""
        config = self.base_config.copy()
        
        # Handle template-based configuration first
        if answers.get("use_template") and answers.get("template_choice"):
            template_config = self._get_template_config(answers["template_choice"])
            config = self._merge_configs(config, template_config)
            # Skip other mappings if using template
            return config
        
        # Apply mappings in order of dependencies
        self._apply_use_case_mapping(config, answers)
        self._apply_retention_mapping(config, answers)
        self._apply_importance_mapping(config, answers)
        self._apply_storage_mapping(config, answers)
        self._apply_content_priorities_mapping(config, answers)
        self._apply_performance_mapping(config, answers)
        self._apply_server_mapping(config, answers)
        self._apply_domain_mapping(config, answers)
        self._apply_advanced_mappings(config, answers)
        
        return config
    
    def _get_base_config(self) -> Dict[str, Any]:
        """Get the base configuration template."""
        return {
            "database": {
                "persist_directory": "./data/memory",
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
                },
                "content_scoring": {
                    "code_bonus": 0.3,
                    "error_bonus": 0.2,
                    "language_bonus": 0.1,
                    "solution_bonus": 0.3,
                    "important_bonus": 0.2
                },
                "permanence_factors": {
                    "architecture_decision": 0.2,
                    "critical_bug_fix": 0.15,
                    "core_documentation": 0.1,
                    "user_explicit_permanent": 0.25,
                    "system_configuration": 0.1
                },
                "domain_patterns": {
                    "case_sensitive": False,
                    "patterns": {
                        "software_development": {
                            "keywords": ["def ", "class ", "function", "import", "return", "bug", "error", "fix", "solution"],
                            "bonus": 0.3,
                            "match_mode": "any"
                        },
                        "architecture": {
                            "keywords": ["design", "pattern", "architecture", "structure", "api", "endpoint"],
                            "bonus": 0.35,
                            "match_mode": "any"
                        },
                        "critical_content": {
                            "keywords": ["critical", "important", "urgent", "breaking", "major"],
                            "bonus": 0.4,
                            "match_mode": "any"
                        }
                    },
                    "permanence_triggers": {
                        "high_importance": {
                            "keywords": ["architecture", "critical", "breakthrough", "major discovery"],
                            "boost": 0.25
                        },
                        "explicit_permanent": {
                            "keywords": ["remember", "permanent", "keep forever", "never delete"],
                            "boost": 0.3
                        }
                    }
                }
            },
            "memory_management": {
                "short_term_max_size": 100,
                "consolidation_threshold": 50,
                "maintenance_interval_hours": 1,
                "consolidation_interval_hours": 6,
                "stats_interval_hours": 24
            },
            "lifecycle": {
                "ttl": {
                    "high_frequency_base": 300,      # 5 minutes
                    "high_frequency_jitter": 60,     # ±1 minute
                    "medium_frequency_base": 3600,   # 1 hour
                    "medium_frequency_jitter": 600,  # ±10 minutes
                    "low_frequency_base": 86400,     # 1 day
                    "low_frequency_jitter": 7200,    # ±2 hours
                    "static_base": 604800,           # 1 week
                    "static_jitter": 86400           # ±1 day
                },
                "aging": {
                    "enabled": True,
                    "decay_rate": 0.1,
                    "minimum_score": 0.1,
                    "refresh_threshold_days": 7.0
                },
                "maintenance": {
                    "enabled": True,
                    "cleanup_interval_hours": 1,
                    "consolidation_interval_hours": 6,
                    "statistics_interval_hours": 24,
                    "deep_maintenance_interval_hours": 168
                }
            },
            "server": {
                "host": "127.0.0.1",
                "port": 8081,
                "title": "Advanced Project Memory MCP Server",
                "version": "2.0.0",
                "protocol_version": "2025-06-18"
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": "logs/mcp_server.log"
            }
        }
    
    def _apply_use_case_mapping(self, config: Dict[str, Any], answers: Dict[str, Any]):
        """Apply use case specific optimizations."""
        use_case = answers.get("use_case")
        
        if use_case == "development":
            # Optimize for code content
            config["memory_scoring"]["content_scoring"]["code_bonus"] = 0.4
            config["memory_scoring"]["content_scoring"]["error_bonus"] = 0.3
            config["memory_scoring"]["content_scoring"]["solution_bonus"] = 0.4
            
        elif use_case == "research":
            # Optimize for long-term retention and documentation
            config["memory_scoring"]["importance_threshold"] = 0.6
            config["memory_scoring"]["content_scoring"]["important_bonus"] = 0.3
            config["lifecycle"]["ttl"]["static_base"] = 1296000  # 15 days
            
        elif use_case == "creative":
            # Balance recency and relevance
            config["memory_scoring"]["scoring_weights"]["recency"] = 0.35
            config["memory_scoring"]["scoring_weights"]["semantic"] = 0.45
            
        elif use_case == "business":
            # Emphasize recent and frequent access
            config["memory_scoring"]["scoring_weights"]["recency"] = 0.4
            config["memory_scoring"]["scoring_weights"]["frequency"] = 0.3
            config["memory_scoring"]["scoring_weights"]["semantic"] = 0.3
    
    def _apply_retention_mapping(self, config: Dict[str, Any], answers: Dict[str, Any]):
        """Apply retention strategy mapping to TTL settings."""
        retention = answers.get("retention_strategy")
        
        if retention == "session_based":
            # Hours-based retention
            config["lifecycle"]["ttl"]["static_base"] = 28800      # 8 hours
            config["lifecycle"]["ttl"]["static_jitter"] = 3600     # ±1 hour
            config["lifecycle"]["ttl"]["low_frequency_base"] = 14400  # 4 hours
            
        elif retention == "daily":
            # Few days retention
            config["lifecycle"]["ttl"]["static_base"] = 259200     # 3 days
            config["lifecycle"]["ttl"]["static_jitter"] = 43200    # ±12 hours
            config["lifecycle"]["ttl"]["low_frequency_base"] = 172800  # 2 days
            
        elif retention == "weekly":
            # Default week-based (already set in base)
            pass
            
        elif retention == "monthly":
            # Extended retention
            config["lifecycle"]["ttl"]["static_base"] = 2592000    # 30 days
            config["lifecycle"]["ttl"]["static_jitter"] = 259200   # ±3 days
            config["lifecycle"]["ttl"]["low_frequency_base"] = 1296000  # 15 days
            
        elif retention == "permanent":
            # Disable TTL aging
            config["lifecycle"]["aging"]["enabled"] = False
            config["lifecycle"]["ttl"]["static_base"] = None
    
    def _apply_importance_mapping(self, config: Dict[str, Any], answers: Dict[str, Any]):
        """Apply importance factors to scoring weights."""
        importance = answers.get("importance_factors")
        
        weights = config["memory_scoring"]["scoring_weights"]
        
        if importance == "recency_focused":
            weights["recency"] = 0.5
            weights["semantic"] = 0.3
            weights["frequency"] = 0.15
            weights["importance"] = 0.05
            
        elif importance == "relevance_focused":
            weights["semantic"] = 0.5
            weights["recency"] = 0.25
            weights["frequency"] = 0.15
            weights["importance"] = 0.1
            
        elif importance == "frequency_focused":
            weights["frequency"] = 0.4
            weights["semantic"] = 0.35
            weights["recency"] = 0.15
            weights["importance"] = 0.1
            
        elif importance == "balanced":
            weights["semantic"] = 0.25
            weights["recency"] = 0.25
            weights["frequency"] = 0.25
            weights["importance"] = 0.25
    
    def _apply_storage_mapping(self, config: Dict[str, Any], answers: Dict[str, Any]):
        """Apply storage preferences to collection sizes and maintenance."""
        storage = answers.get("storage_preference")
        
        mgmt = config["memory_management"]
        maint = config["lifecycle"]["maintenance"]
        
        if storage == "minimal":
            mgmt["short_term_max_size"] = 50
            mgmt["consolidation_threshold"] = 25
            mgmt["maintenance_interval_hours"] = 0.5  # 30 minutes
            maint["cleanup_interval_hours"] = 0.5
            
        elif storage == "standard":
            # Default values (already set)
            pass
            
        elif storage == "large":
            mgmt["short_term_max_size"] = 200
            mgmt["consolidation_threshold"] = 100
            mgmt["maintenance_interval_hours"] = 2
            maint["cleanup_interval_hours"] = 2
            
        elif storage == "unlimited":
            mgmt["short_term_max_size"] = 500
            mgmt["consolidation_threshold"] = 250
            mgmt["maintenance_interval_hours"] = 6
            maint["cleanup_interval_hours"] = 6
            config["memory_scoring"]["importance_threshold"] = 0.5  # Lower threshold
    
    def _apply_content_priorities_mapping(self, config: Dict[str, Any], answers: Dict[str, Any]):
        """Apply content type priorities to scoring bonuses."""
        priorities = answers.get("content_priorities", [])
        
        content_scoring = config["memory_scoring"]["content_scoring"]
        patterns = config["memory_scoring"]["domain_patterns"]["patterns"]
        
        # Reset all bonuses to base level
        base_bonus = 0.2
        enhanced_bonus = 0.4
        
        # Set base bonuses
        content_scoring["code_bonus"] = base_bonus
        content_scoring["error_bonus"] = base_bonus
        content_scoring["important_bonus"] = base_bonus
        content_scoring["solution_bonus"] = base_bonus
        patterns["software_development"]["bonus"] = base_bonus
        patterns["architecture"]["bonus"] = base_bonus
        patterns["critical_content"]["bonus"] = base_bonus
        
        # Enhance selected priorities
        if "code" in priorities:
            content_scoring["code_bonus"] = enhanced_bonus
            content_scoring["solution_bonus"] = enhanced_bonus
            patterns["software_development"]["bonus"] = enhanced_bonus
            
        if "errors" in priorities:
            content_scoring["error_bonus"] = enhanced_bonus
            
        if "architecture" in priorities:
            patterns["architecture"]["bonus"] = enhanced_bonus
            config["memory_scoring"]["permanence_factors"]["architecture_decision"] = 0.3
            
        if "critical" in priorities:
            patterns["critical_content"]["bonus"] = enhanced_bonus
            content_scoring["important_bonus"] = enhanced_bonus
            
        if "documentation" in priorities:
            config["memory_scoring"]["permanence_factors"]["core_documentation"] = 0.2
    
    def _apply_performance_mapping(self, config: Dict[str, Any], answers: Dict[str, Any]):
        """Apply performance preferences to maintenance intervals."""
        performance = answers.get("performance_preference")
        
        maint = config["lifecycle"]["maintenance"]
        mgmt = config["memory_management"]
        
        if performance == "performance":
            # Less frequent maintenance
            maint["cleanup_interval_hours"] = 2
            maint["consolidation_interval_hours"] = 12
            maint["statistics_interval_hours"] = 48
            mgmt["maintenance_interval_hours"] = 2
            
        elif performance == "balanced":
            # Default values (already set)
            pass
            
        elif performance == "accuracy":
            # More frequent maintenance
            maint["cleanup_interval_hours"] = 0.5
            maint["consolidation_interval_hours"] = 3
            maint["statistics_interval_hours"] = 12
            mgmt["maintenance_interval_hours"] = 0.5
    
    def _apply_advanced_mappings(self, config: Dict[str, Any], answers: Dict[str, Any]):
        """Apply advanced settings if configured."""
        if not answers.get("advanced_settings"):
            return
        
        # Custom importance threshold
        if "importance_threshold" in answers:
            config["memory_scoring"]["importance_threshold"] = answers["importance_threshold"]
        
        # Consolidation frequency
        consolidation = answers.get("consolidation_frequency")
        if consolidation == "frequent":
            config["memory_management"]["consolidation_interval_hours"] = 2
            config["lifecycle"]["maintenance"]["consolidation_interval_hours"] = 2
        elif consolidation == "infrequent":
            config["memory_management"]["consolidation_interval_hours"] = 24
            config["lifecycle"]["maintenance"]["consolidation_interval_hours"] = 24
    
    def _get_template_config(self, template_name: str) -> Dict[str, Any]:
        """Get configuration from a template."""
        from .templates import ConfigTemplates
        return ConfigTemplates.get_template(template_name)
    
    def _merge_configs(self, base: Dict[str, Any], template: Dict[str, Any]) -> Dict[str, Any]:
        """Merge template configuration into base configuration."""
        import copy
        merged = copy.deepcopy(base)
        
        def deep_merge(target: Dict[str, Any], source: Dict[str, Any]):
            for key, value in source.items():
                if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                    deep_merge(target[key], value)
                else:
                    target[key] = value
        
        deep_merge(merged, template)
        return merged
    
    def _apply_server_mapping(self, config: Dict[str, Any], answers: Dict[str, Any]):
        """Apply server configuration mapping."""
        server_config = config.setdefault("server", {})
        
        # Host configuration
        accessibility = answers.get("server_accessibility")
        if accessibility == "localhost":
            server_config["host"] = "127.0.0.1"
        elif accessibility == "network":
            server_config["host"] = "0.0.0.0"
        elif accessibility == "custom" and answers.get("custom_host"):
            server_config["host"] = answers["custom_host"]
        
        # Port configuration
        if "server_port" in answers:
            server_config["port"] = int(answers["server_port"])
        
        # Title configuration
        if "server_title" in answers:
            server_config["title"] = answers["server_title"]
    
    def _apply_domain_mapping(self, config: Dict[str, Any], answers: Dict[str, Any]):
        """Apply domain pattern configuration mapping."""
        if not answers.get("customize_domains"):
            return
        
        domain_categories = answers.get("domain_categories", [])
        patterns = config["memory_scoring"]["domain_patterns"]["patterns"]
        
        # Add custom domain patterns based on selected categories
        if "technology" in domain_categories and answers.get("tech_keywords"):
            keywords = [kw.strip() for kw in answers["tech_keywords"].split(",") if kw.strip()]
            if keywords:
                patterns["custom_technology"] = {
                    "keywords": keywords,
                    "bonus": 0.35,
                    "match_mode": "any"
                }
        
        if "business" in domain_categories and answers.get("business_keywords"):
            keywords = [kw.strip() for kw in answers["business_keywords"].split(",") if kw.strip()]
            if keywords:
                patterns["custom_business"] = {
                    "keywords": keywords,
                    "bonus": 0.3,
                    "match_mode": "any"
                }
        
        if "research" in domain_categories and answers.get("research_keywords"):
            keywords = [kw.strip() for kw in answers["research_keywords"].split(",") if kw.strip()]
            if keywords:
                patterns["custom_research"] = {
                    "keywords": keywords,
                    "bonus": 0.3,
                    "match_mode": "any"
                }
        
        if "creative" in domain_categories and answers.get("creative_keywords"):
            keywords = [kw.strip() for kw in answers["creative_keywords"].split(",") if kw.strip()]
            if keywords:
                patterns["custom_creative"] = {
                    "keywords": keywords,
                    "bonus": 0.25,
                    "match_mode": "any"
                }


class ConfigAnalyzer:
    """Analyzes existing configuration and explains it in human terms."""
    
    def analyze_config(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Analyze a configuration and return human-readable explanations."""
        explanations = {}
        
        # Analyze retention strategy
        static_base = config.get("lifecycle", {}).get("ttl", {}).get("static_base")
        if static_base is None:
            explanations["retention"] = "Permanent retention (until manually deleted)"
        elif static_base <= 28800:  # 8 hours
            explanations["retention"] = "Session-based retention (hours)"
        elif static_base <= 259200:  # 3 days  
            explanations["retention"] = "Short-term retention (few days)"
        elif static_base <= 604800:  # 1 week
            explanations["retention"] = "Weekly retention (about a week)"
        else:
            explanations["retention"] = "Long-term retention (weeks to months)"
        
        # Analyze importance factors
        weights = config.get("memory_scoring", {}).get("scoring_weights", {})
        max_weight = max(weights.values()) if weights else 0
        max_factor = max(weights, key=weights.get) if weights else "unknown"
        
        factor_names = {
            "semantic": "content relevance",
            "recency": "recent activity", 
            "frequency": "access frequency",
            "importance": "explicit importance"
        }
        
        explanations["importance"] = f"Prioritizes {factor_names.get(max_factor, max_factor)} (weight: {max_weight:.1f})"
        
        # Analyze storage preference
        short_term_size = config.get("memory_management", {}).get("short_term_max_size", 100)
        if short_term_size <= 50:
            explanations["storage"] = "Minimal storage (aggressive cleanup)"
        elif short_term_size <= 100:
            explanations["storage"] = "Standard storage (balanced)"
        elif short_term_size <= 200:
            explanations["storage"] = "Large storage (more retention)"
        else:
            explanations["storage"] = "Maximum storage (minimal cleanup)"
        
        # Analyze maintenance frequency
        cleanup_interval = config.get("lifecycle", {}).get("maintenance", {}).get("cleanup_interval_hours", 1)
        if cleanup_interval <= 0.5:
            explanations["performance"] = "Accuracy-focused (frequent maintenance)"
        elif cleanup_interval <= 1:
            explanations["performance"] = "Balanced performance"
        else:
            explanations["performance"] = "Performance-focused (less maintenance)"
        
        return explanations