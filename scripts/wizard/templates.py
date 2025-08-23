"""
Configuration templates and profiles for common use cases.

This module provides pre-built configuration templates that can be used
as starting points or quick setup options.
"""

from typing import Dict, Any, List


class ConfigTemplates:
    """Pre-built configuration templates for common use cases."""
    
    @staticmethod
    def get_available_templates() -> Dict[str, str]:
        """Get available template names and descriptions."""
        return {
            "development": "Optimized for software development work",
            "research": "Optimized for research and analysis",
            "creative": "Optimized for creative writing and brainstorming",
            "business": "Optimized for business operations and meetings",
            "minimal": "Minimal resource usage, fast cleanup",
            "maximum": "Maximum retention, extensive storage"
        }
    
    @staticmethod
    def get_template(template_name: str) -> Dict[str, Any]:
        """Get a specific configuration template."""
        templates = {
            "development": ConfigTemplates._development_template(),
            "research": ConfigTemplates._research_template(),
            "creative": ConfigTemplates._creative_template(),
            "business": ConfigTemplates._business_template(),
            "minimal": ConfigTemplates._minimal_template(),
            "maximum": ConfigTemplates._maximum_template()
        }
        
        return templates.get(template_name, {})
    
    @staticmethod
    def _development_template() -> Dict[str, Any]:
        """Template optimized for software development."""
        return {
            "database": {
                "persist_directory": "./data/memory",
                "collections": {
                    "short_term": "short_term_memory",
                    "long_term": "long_term_memory",
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
                    "code_bonus": 0.4,
                    "error_bonus": 0.3,
                    "language_bonus": 0.1,
                    "solution_bonus": 0.4,
                    "important_bonus": 0.2
                }
            },
            "memory_management": {
                "short_term_max_size": 100,
                "maintenance_interval_hours": 1,
                "stats_interval_hours": 24
            },
            "lifecycle": {
                "ttl": {
                    "static_base": 604800,  # 1 week
                    "static_jitter": 86400
                },
                "aging": {
                    "enabled": True,
                    "decay_rate": 0.1
                }
            }
        }
    
    @staticmethod
    def _research_template() -> Dict[str, Any]:
        """Template optimized for research and analysis."""
        return {
            "memory_scoring": {
                "importance_threshold": 0.6,  # Lower threshold for research
                "scoring_weights": {
                    "semantic": 0.5,
                    "recency": 0.25,
                    "frequency": 0.15,
                    "importance": 0.1
                },
                "content_scoring": {
                    "code_bonus": 0.2,
                    "error_bonus": 0.2,
                    "language_bonus": 0.1,
                    "solution_bonus": 0.3,
                    "important_bonus": 0.3
                }
            },
            "lifecycle": {
                "ttl": {
                    "static_base": 1296000,  # 15 days
                    "static_jitter": 172800   # ±2 days
                }
            }
        }
    
    @staticmethod
    def _creative_template() -> Dict[str, Any]:
        """Template optimized for creative work."""
        return {
            "memory_scoring": {
                "scoring_weights": {
                    "semantic": 0.45,
                    "recency": 0.35,
                    "frequency": 0.15,
                    "importance": 0.05
                }
            },
            "memory_management": {
                "short_term_max_size": 150
            }
        }
    
    @staticmethod
    def _business_template() -> Dict[str, Any]:
        """Template optimized for business operations."""
        return {
            "memory_scoring": {
                "scoring_weights": {
                    "semantic": 0.3,
                    "recency": 0.4,
                    "frequency": 0.3,
                    "importance": 0.0
                }
            },
            "lifecycle": {
                "ttl": {
                    "static_base": 432000,  # 5 days
                    "static_jitter": 43200   # ±12 hours
                }
            }
        }
    
    @staticmethod
    def _minimal_template() -> Dict[str, Any]:
        """Template for minimal resource usage."""
        return {
            "memory_management": {
                "short_term_max_size": 50,
                "maintenance_interval_hours": 0.5,
                "stats_interval_hours": 12
            },
            "lifecycle": {
                "ttl": {
                    "static_base": 259200,  # 3 days
                    "static_jitter": 43200
                },
                "maintenance": {
                    "cleanup_interval_hours": 0.5
                }
            }
        }
    
    @staticmethod
    def _maximum_template() -> Dict[str, Any]:
        """Template for maximum retention."""
        return {
            "memory_scoring": {
                "importance_threshold": 0.5  # Lower threshold
            },
            "memory_management": {
                "short_term_max_size": 500,
                "maintenance_interval_hours": 6,
                "stats_interval_hours": 48
            },
            "lifecycle": {
                "ttl": {
                    "static_base": 2592000,  # 30 days
                    "static_jitter": 259200
                },
                "aging": {
                    "enabled": False  # Disable aging for maximum retention
                },
                "maintenance": {
                    "cleanup_interval_hours": 6
                }
            }
        }


class ConfigProfiler:
    """Analyzes usage patterns and suggests optimal configurations."""
    
    def suggest_template(self, usage_data: Dict[str, Any]) -> str:
        """Suggest the best template based on usage patterns."""
        # This could analyze actual usage patterns in the future
        # For now, provide basic heuristics
        
        query_frequency = usage_data.get("queries_per_hour", 10)
        document_types = usage_data.get("document_types", [])
        retention_needs = usage_data.get("retention_days", 7)
        
        if "code" in document_types and query_frequency > 20:
            return "development"
        elif retention_needs > 14:
            return "research"
        elif query_frequency < 5:
            return "minimal"
        else:
            return "development"  # Safe default
    
    def optimize_config(self, config: Dict[str, Any], usage_data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize an existing configuration based on usage patterns."""
        optimized = config.copy()
        
        # Adjust based on query frequency
        query_frequency = usage_data.get("queries_per_hour", 10)
        if query_frequency > 50:
            # High frequency - optimize for performance
            optimized.setdefault("memory_management", {})["maintenance_interval_hours"] = 2
        elif query_frequency < 5:
            # Low frequency - optimize for resources
            optimized.setdefault("memory_management", {})["short_term_max_size"] = 50
        
        # Adjust based on storage constraints
        storage_gb = usage_data.get("available_storage_gb", 10)
        if storage_gb < 5:
            # Limited storage
            optimized.setdefault("memory_management", {})["short_term_max_size"] = 50
        
        return optimized