#!/usr/bin/env python3
"""
Simple memory backup utility for MCP Memory Server

Creates a timestamped backup of your memory database for safekeeping.
"""

import os
import shutil
import datetime
from pathlib import Path

def create_backup():
    """Create a backup of the current memory database"""
    
    # Paths - check config to get actual database location
    project_root = Path(__file__).parent.parent
    
    # First check default config locations
    config_path = project_root / "config.json"
    memory_dir = project_root / "chroma_db_advanced"  # Default from config.example.json
    
    # Try to read actual config if it exists
    if config_path.exists():
        try:
            import json
            with open(config_path, 'r') as f:
                config = json.load(f)
            memory_dir = Path(config.get('database', {}).get('persist_directory', 'chroma_db_advanced'))
            if not memory_dir.is_absolute():
                memory_dir = project_root / memory_dir
        except:
            pass  # Use default if config can't be read
    
    backups_dir = project_root / "backups"
    
    # Check if memory database exists
    if not memory_dir.exists():
        print("ERROR: No memory database found to backup")
        print(f"Looked for database at: {memory_dir}")
        return False
    
    # Create backup directory
    backups_dir.mkdir(exist_ok=True)
    
    # Create timestamped backup name
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"memory_backup_{timestamp}"
    backup_path = backups_dir / backup_name
    
    try:
        # Copy memory database to backup
        print(f"Creating backup: {backup_name}")
        shutil.copytree(memory_dir, backup_path)
        
        # Get backup size
        total_size = sum(f.stat().st_size for f in backup_path.rglob('*') if f.is_file())
        size_mb = total_size / (1024 * 1024)
        
        print(f"Backup created successfully!")
        print(f"Location: {backup_path}")
        print(f"Size: {size_mb:.1f} MB")
        return True
        
    except Exception as e:
        print(f"ERROR: Backup failed: {e}")
        return False

def list_backups():
    """List all available backups"""
    project_root = Path(__file__).parent.parent
    backups_dir = project_root / "backups"
    
    if not backups_dir.exists():
        print("No backups found")
        return
    
    backups = list(backups_dir.glob("memory_backup_*"))
    if not backups:
        print("No backups found")
        return
    
    print("Available backups:")
    for backup in sorted(backups, reverse=True):
        # Get backup info
        try:
            total_size = sum(f.stat().st_size for f in backup.rglob('*') if f.is_file())
            size_mb = total_size / (1024 * 1024)
            created = datetime.datetime.fromtimestamp(backup.stat().st_mtime)
            print(f"  {backup.name}")
            print(f"     Created: {created.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"     Size: {size_mb:.1f} MB")
            print()
        except Exception as e:
            print(f"  ERROR: {backup.name} (error reading info)")

def main():
    """Main function"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        list_backups()
    else:
        create_backup()

if __name__ == "__main__":
    main()