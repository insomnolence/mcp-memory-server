"""
Test database setup utilities for creating and managing test databases.
"""
import shutil
from pathlib import Path
from typing import Optional
import logging


class DatabaseManager:
    """Manages test database creation, cleanup, and isolation."""

    def __init__(self, base_test_dir: Optional[str] = None):
        """Initialize test DB manager.

        Args:
            base_test_dir: Base directory for test databases. Defaults to tests/temp_test_db
        """
        if base_test_dir is None:
            self.base_test_dir = Path(__file__).parent / "temp_test_db"
        else:
            self.base_test_dir = Path(base_test_dir)

        self.test_instances = {}

    def create_test_db(self, test_name: str, clean: bool = True) -> Path:
        """Create a test database directory.

        Args:
            test_name: Name of the test session (used for directory naming)
            clean: Whether to clean existing database if it exists

        Returns:
            Path to the created test database directory
        """
        # Use simple naming for shared test database
        test_db_path = self.base_test_dir / "shared_test_db"

        if clean and test_db_path.exists():
            self.cleanup_test_db(test_db_path)

        test_db_path.mkdir(parents=True, exist_ok=True)

        # Create logs directory
        logs_dir = Path(__file__).parent / "temp_logs" / "shared_session"
        logs_dir.mkdir(parents=True, exist_ok=True)

        self.test_instances[test_name] = {
            'db_path': test_db_path,
            'logs_dir': logs_dir
        }

        logging.info(f"Created test database: {test_db_path}")
        return test_db_path

    def cleanup_test_db(self, db_path: Path):
        """Clean up a test database directory.

        Args:
            db_path: Path to the test database directory to clean up
        """
        if db_path.exists():
            try:
                shutil.rmtree(db_path)
                logging.info(f"Cleaned up test database: {db_path}")
            except Exception as e:
                logging.warning(f"Failed to cleanup test database {db_path}: {e}")

    def cleanup_all_test_dbs(self):
        """Clean up all test databases created by this manager."""
        if self.base_test_dir.exists():
            try:
                shutil.rmtree(self.base_test_dir)
                logging.info(f"Cleaned up all test databases in: {self.base_test_dir}")
            except Exception as e:
                logging.warning(f"Failed to cleanup all test databases: {e}")

        # Also cleanup logs
        logs_base = Path(__file__).parent / "temp_logs"
        if logs_base.exists():
            try:
                shutil.rmtree(logs_base)
                logging.info(f"Cleaned up all test logs in: {logs_base}")
            except Exception as e:
                logging.warning(f"Failed to cleanup test logs: {e}")

    def get_test_config_path(self) -> Path:
        """Get the path to the test configuration file."""
        return Path(__file__).parent / "test_config.json"

    def create_isolated_config(self, test_name: str, port: int = 8080,
                               enable_deduplication: bool = True,
                               ttl_fast_mode: bool = True) -> Path:
        """Create a config file for the test session.

        Args:
            test_name: Name of the test session
            port: Port for the server to use
            enable_deduplication: Whether to enable deduplication
            ttl_fast_mode: Whether to use fast TTL times for testing

        Returns:
            Path to the created config file
        """
        import json

        # Load base test config
        base_config_path = self.get_test_config_path()
        with open(base_config_path, 'r') as f:
            config = json.load(f)

        # Create test-specific database path
        test_db_path = self.create_test_db(test_name, clean=True)

        # Update config for this specific test
        config["database"]["persist_directory"] = str(test_db_path)
        config["server"]["port"] = port
        config["deduplication"]["enabled"] = enable_deduplication

        if ttl_fast_mode:
            # Use very fast TTL for testing (seconds instead of minutes/hours)
            config["lifecycle"]["ttl"].update({
                "high_frequency_base": 5,     # 5 seconds instead of 30
                "high_frequency_jitter": 1,   # 1 second jitter
                "medium_frequency_base": 15,  # 15 seconds instead of 5 minutes
                "medium_frequency_jitter": 3,  # 3 seconds jitter
                "low_frequency_base": 60,     # 1 minute instead of 1 hour
                "low_frequency_jitter": 10,   # 10 seconds jitter
                "static_base": 300,           # 5 minutes instead of 6 hours
                "static_jitter": 30           # 30 seconds jitter
            })
            # Also speed up maintenance cycles
            config["lifecycle"]["maintenance"].update({
                "cleanup_interval_hours": 0.001,  # ~3.6 seconds
                "consolidation_interval_hours": 0.01,  # ~36 seconds
            })

        # Create shared test config file
        config_path = Path(__file__).parent / "temp_configs" / "shared_test_config.json"
        config_path.parent.mkdir(exist_ok=True)

        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        logging.info(f"Created shared test config: {config_path}")
        return config_path


# Global test database manager instance
_test_db_manager = None


def get_test_db_manager() -> DatabaseManager:
    """Get the global test database manager instance."""
    global _test_db_manager
    if _test_db_manager is None:
        _test_db_manager = DatabaseManager()
    return _test_db_manager


def setup_test_environment(test_name: str, **config_overrides) -> dict:
    """Set up a complete test environment with database and config.

    Args:
        test_name: Name of the test
        **config_overrides: Additional config overrides

    Returns:
        Dict with 'db_path', 'config_path', 'port' for the test environment
    """
    manager = get_test_db_manager()

    # Extract specific parameters and pass the rest
    port = config_overrides.pop('port', 8080 + hash(test_name) % 1000)
    enable_deduplication = config_overrides.pop('enable_deduplication', True)
    ttl_fast_mode = config_overrides.pop('ttl_fast_mode', True)

    config_path = manager.create_isolated_config(
        test_name=test_name,
        port=port,
        enable_deduplication=enable_deduplication,
        ttl_fast_mode=ttl_fast_mode
    )

    db_path = manager.test_instances[test_name]['db_path']

    return {
        'db_path': db_path,
        'config_path': config_path,
        'port': port,
        'logs_dir': manager.test_instances[test_name]['logs_dir']
    }


def cleanup_test_environment():
    """Clean up all test environments."""
    manager = get_test_db_manager()
    manager.cleanup_all_test_dbs()

    # Also cleanup temp configs
    temp_configs = Path(__file__).parent / "temp_configs"
    if temp_configs.exists():
        try:
            shutil.rmtree(temp_configs)
            logging.info(f"Cleaned up temp configs: {temp_configs}")
        except Exception as e:
            logging.warning(f"Failed to cleanup temp configs: {e}")
