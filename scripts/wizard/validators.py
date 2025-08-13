"""
Configuration validation and preview system.

This module validates configurations and provides human-readable previews
of what the configuration choices will mean in practice.
"""

from typing import Dict, Any, List, Tuple, Optional
import json
from pathlib import Path


class ConfigValidator:
    """Validates configuration for completeness and correctness."""
    
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a configuration dictionary.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate required sections
        required_sections = [
            "database", "embeddings", "memory_scoring", 
            "memory_management", "lifecycle", "server"
        ]
        
        for section in required_sections:
            if section not in config:
                errors.append(f"Missing required section: {section}")
        
        # Validate database config
        if "database" in config:
            db_config = config["database"]
            if "persist_directory" not in db_config:
                errors.append("Database config missing persist_directory")
            if "collections" not in db_config:
                errors.append("Database config missing collections")
        
        # Validate scoring weights sum to 1.0
        if "memory_scoring" in config:
            scoring = config["memory_scoring"]
            if "scoring_weights" in scoring:
                weights = scoring["scoring_weights"]
                total = sum(weights.values())
                if abs(total - 1.0) > 0.01:  # Allow small floating point errors
                    errors.append(f"Scoring weights sum to {total:.3f}, should sum to 1.0")
            
            # Validate importance threshold
            if "importance_threshold" in scoring:
                threshold = scoring["importance_threshold"]
                if not 0.0 <= threshold <= 1.0:
                    errors.append(f"Importance threshold {threshold} must be between 0.0 and 1.0")
        
        # Validate TTL values
        if "lifecycle" in config and "ttl" in config["lifecycle"]:
            ttl_config = config["lifecycle"]["ttl"]
            ttl_fields = ["high_frequency_base", "medium_frequency_base", "low_frequency_base"]
            
            for field in ttl_fields:
                if field in ttl_config and ttl_config[field] is not None:
                    if ttl_config[field] <= 0:
                        errors.append(f"TTL {field} must be positive, got {ttl_config[field]}")
        
        # Validate server config
        if "server" in config:
            server = config["server"]
            if "port" in server:
                port = server["port"]
                if not isinstance(port, int) or not 1 <= port <= 65535:
                    errors.append(f"Server port {port} must be an integer between 1 and 65535")
        
        return len(errors) == 0, errors
    
    def validate_answer(self, question_id: str, answer: Any, question_config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate a single answer against question constraints.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        validation = question_config.get("validation", {})
        
        if question_config.get("required", True) and answer is None:
            return False, "This question requires an answer"
        
        if answer is None:
            return True, None  # Optional question
        
        # Numeric validation
        if "min" in validation and answer < validation["min"]:
            return False, f"Value must be at least {validation['min']}"
        
        if "max" in validation and answer > validation["max"]:
            return False, f"Value must be at most {validation['max']}"
        
        return True, None


class ConfigPreview:
    """Provides human-readable previews of configuration impact."""
    
    def generate_preview(self, config: Dict[str, Any], answers: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a comprehensive preview of configuration impact."""
        preview = {
            "summary": self._generate_summary(answers),
            "memory_behavior": self._preview_memory_behavior(config),
            "performance_impact": self._preview_performance_impact(config),
            "storage_usage": self._preview_storage_usage(config),
            "maintenance_schedule": self._preview_maintenance_schedule(config),
            "examples": self._generate_examples(config, answers)
        }
        
        return preview
    
    def _generate_summary(self, answers: Dict[str, Any]) -> str:
        """Generate a high-level summary of choices."""
        use_case = answers.get("use_case", "general")
        retention = answers.get("retention_strategy", "weekly") 
        importance = answers.get("importance_factors", "balanced")
        storage = answers.get("storage_preference", "standard")
        
        use_case_names = {
            "development": "Software Development",
            "research": "Research & Analysis", 
            "creative": "Creative Work",
            "business": "Business Operations",
            "general": "General Purpose"
        }
        
        retention_names = {
            "session_based": "session-based (hours)",
            "daily": "short-term (few days)",
            "weekly": "weekly",
            "monthly": "long-term (weeks to months)",
            "permanent": "permanent"
        }
        
        return (f"Configured for {use_case_names.get(use_case, use_case)} use case "
                f"with {retention_names.get(retention, retention)} retention, "
                f"{importance.replace('_', ' ')} importance weighting, "
                f"and {storage} storage allocation.")
    
    def _preview_memory_behavior(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Preview how memory will behave with this configuration."""
        behavior = {}
        
        # TTL behavior
        ttl_config = config.get("lifecycle", {}).get("ttl", {})
        static_base = ttl_config.get("static_base")
        
        if static_base is None:
            behavior["retention"] = "Memories persist until manually deleted"
        else:
            days = static_base / 86400
            if days < 1:
                hours = static_base / 3600
                behavior["retention"] = f"Memories expire after ~{hours:.1f} hours"
            else:
                behavior["retention"] = f"Memories expire after ~{days:.1f} days"
        
        # Importance threshold
        threshold = config.get("memory_scoring", {}).get("importance_threshold", 0.7)
        behavior["long_term_promotion"] = f"Content with importance ≥ {threshold:.1f} moves to long-term storage"
        
        # Scoring weights
        weights = config.get("memory_scoring", {}).get("scoring_weights", {})
        max_factor = max(weights, key=weights.get) if weights else "unknown"
        factor_names = {
            "semantic": "content relevance",
            "recency": "recent activity",
            "frequency": "access frequency", 
            "importance": "explicit importance"
        }
        behavior["prioritization"] = f"Prioritizes {factor_names.get(max_factor, max_factor)} when ranking memories"
        
        return behavior
    
    def _preview_performance_impact(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Preview performance characteristics."""
        performance = {}
        
        # Maintenance frequency
        cleanup_interval = config.get("lifecycle", {}).get("maintenance", {}).get("cleanup_interval_hours", 1)
        if cleanup_interval <= 0.5:
            performance["maintenance"] = "High frequency maintenance (better accuracy, more CPU usage)"
        elif cleanup_interval <= 1:
            performance["maintenance"] = "Balanced maintenance (good accuracy and performance)"
        else:
            performance["maintenance"] = "Low frequency maintenance (better performance, less accuracy)"
        
        # Collection sizes
        short_term_size = config.get("memory_management", {}).get("short_term_max_size", 100)
        performance["memory_footprint"] = f"Short-term memory limited to {short_term_size} items"
        
        # Aging settings
        aging_enabled = config.get("lifecycle", {}).get("aging", {}).get("enabled", True)
        if aging_enabled:
            decay_rate = config.get("lifecycle", {}).get("aging", {}).get("decay_rate", 0.1)
            performance["aging"] = f"Memory importance decays at {decay_rate*100:.0f}% per refresh cycle"
        else:
            performance["aging"] = "Memory aging disabled - importance scores remain constant"
        
        return performance
    
    def _preview_storage_usage(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Preview storage usage characteristics."""
        storage = {}
        
        # Collection sizes
        mgmt = config.get("memory_management", {})
        short_term_size = mgmt.get("short_term_max_size", 100)
        consolidation_threshold = mgmt.get("consolidation_threshold", 50)
        
        storage["capacity"] = f"Up to {short_term_size} items in active memory"
        storage["consolidation"] = f"Memories consolidated when short-term reaches {consolidation_threshold} items"
        
        # Persistence directory
        persist_dir = config.get("database", {}).get("persist_directory", "./data/memory")
        storage["location"] = f"Data persisted to: {persist_dir}"
        
        return storage
    
    def _preview_maintenance_schedule(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Preview maintenance schedule."""
        schedule = {}
        
        maint = config.get("lifecycle", {}).get("maintenance", {})
        mgmt = config.get("memory_management", {})
        
        cleanup_hours = maint.get("cleanup_interval_hours", 1)
        consolidation_hours = maint.get("consolidation_interval_hours", 6)
        stats_hours = maint.get("statistics_interval_hours", 24)
        
        schedule["cleanup"] = f"Memory cleanup every {cleanup_hours} hours"
        schedule["consolidation"] = f"Memory consolidation every {consolidation_hours} hours"
        schedule["statistics"] = f"Statistics update every {stats_hours} hours"
        
        return schedule
    
    def _generate_examples(self, config: Dict[str, Any], answers: Dict[str, Any]) -> Dict[str, str]:
        """Generate concrete examples of how the system will behave."""
        examples = {}
        
        use_case = answers.get("use_case", "general")
        
        if use_case == "development":
            examples["scenario_1"] = "A code snippet you reference will get a high importance score and move to long-term storage"
            examples["scenario_2"] = "Error messages and stack traces will be prioritized and remembered longer"
            examples["scenario_3"] = "Architecture decisions will be marked as permanent and never expire"
        
        elif use_case == "research":
            examples["scenario_1"] = "Important research findings will be retained for extended periods"
            examples["scenario_2"] = "Documentation and explanations will receive importance bonuses"
            examples["scenario_3"] = "Related research papers will be consolidated into summaries"
        
        elif use_case == "creative":
            examples["scenario_1"] = "Recent creative ideas will be weighted heavily in search results"
            examples["scenario_2"] = "Frequently referenced concepts will build up importance over time"
            examples["scenario_3"] = "Creative iterations will be tracked and compared"
        
        elif use_case == "business":
            examples["scenario_1"] = "Recent meeting notes will be prioritized in search results"
            examples["scenario_2"] = "Frequently accessed customer information will be retained longer"
            examples["scenario_3"] = "Critical business decisions will be marked for permanent retention"
        
        else:  # general
            examples["scenario_1"] = "Important content will be automatically identified and prioritized"
            examples["scenario_2"] = "Frequently accessed information will build up importance scores"
            examples["scenario_3"] = "Related memories will be consolidated to save space"
        
        return examples


class ConfigComparison:
    """Compare configurations and highlight differences."""
    
    def compare_configs(self, old_config: Dict[str, Any], new_config: Dict[str, Any]) -> Dict[str, Any]:
        """Compare two configurations and highlight key differences."""
        differences = {
            "changed_sections": [],
            "key_changes": {},
            "impact_summary": ""
        }
        
        # Compare key sections
        sections_to_compare = [
            ("memory_scoring.scoring_weights", "Importance factor weights"),
            ("memory_scoring.importance_threshold", "Long-term storage threshold"),
            ("lifecycle.ttl.static_base", "Base memory retention time"),
            ("memory_management.short_term_max_size", "Short-term memory capacity"),
            ("lifecycle.maintenance.cleanup_interval_hours", "Cleanup frequency")
        ]
        
        for path, description in sections_to_compare:
            old_val = self._get_nested_value(old_config, path)
            new_val = self._get_nested_value(new_config, path)
            
            if old_val != new_val:
                differences["key_changes"][description] = {
                    "old": old_val,
                    "new": new_val
                }
        
        # Generate impact summary
        if differences["key_changes"]:
            changes = list(differences["key_changes"].keys())
            differences["impact_summary"] = f"Configuration changes affect: {', '.join(changes)}"
        else:
            differences["impact_summary"] = "No significant changes detected"
        
        return differences
    
    def _get_nested_value(self, config: Dict[str, Any], path: str) -> Any:
        """Get a nested value using dot notation."""
        keys = path.split(".")
        value = config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value