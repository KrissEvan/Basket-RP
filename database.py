import sqlite3
import os
import logging
from typing import Optional
import asyncio

logger = logging.getLogger(__name__)

class DatabaseConnection:
    """Context manager for database connections"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection = None
    
    def __enter__(self):
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row  # Enable column access by name
        return self.connection
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            if exc_type is None:
                self.connection.commit()
            else:
                self.connection.rollback()
            self.connection.close()

async def init_db():
    """Initialize the database with required tables"""
    db_path = os.getenv('DATABASE_PATH', 'basketball_bot.db')
    
    try:
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            
            # Create player_profiles table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS player_profiles (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL,
                    archetype TEXT NOT NULL DEFAULT 'Généraliste',
                    stats TEXT NOT NULL,
                    available_points INTEGER DEFAULT 0,
                    character_name TEXT,
                    first_name TEXT,
                    age INTEGER,
                    height INTEGER,
                    weight INTEGER,
                    profile_image TEXT,
                    embed_color INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')

            # Add new columns if they don't exist (for existing databases)
            try:
                cursor.execute('ALTER TABLE player_profiles ADD COLUMN character_name TEXT')
            except:
                pass
            try:
                cursor.execute('ALTER TABLE player_profiles ADD COLUMN first_name TEXT')
            except:
                pass
            try:
                cursor.execute('ALTER TABLE player_profiles ADD COLUMN age INTEGER')
            except:
                pass
            try:
                cursor.execute('ALTER TABLE player_profiles ADD COLUMN height INTEGER')
            except:
                pass
            try:
                cursor.execute('ALTER TABLE player_profiles ADD COLUMN weight INTEGER')
            except:
                pass
            try:
                cursor.execute('ALTER TABLE player_profiles ADD COLUMN profile_image TEXT')
            except:
                pass
            try:
                cursor.execute('ALTER TABLE player_profiles ADD COLUMN embed_color INTEGER')
            except:
                pass
            
            # Create action_logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS action_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT,
                    admin_id INTEGER,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES player_profiles (user_id)
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_player_profiles_username 
                ON player_profiles (username)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_action_logs_user_id 
                ON action_logs (user_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_action_logs_timestamp 
                ON action_logs (timestamp)
            ''')
            
            # Create settings table for bot configuration
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bot_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
            
            logger.info("Database tables created successfully")
            
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

async def backup_database(backup_path: Optional[str] = None):
    """Create a backup of the database"""
    if backup_path is None:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"basketball_bot_backup_{timestamp}.db"
    
    db_path = os.getenv('DATABASE_PATH', 'basketball_bot.db')
    
    try:
        # Use sqlite3 backup API for safe backup
        with sqlite3.connect(db_path) as source:
            with sqlite3.connect(backup_path) as backup:
                source.backup(backup)
        
        logger.info(f"Database backup created: {backup_path}")
        return backup_path
        
    except Exception as e:
        logger.error(f"Database backup failed: {e}")
        raise

async def cleanup_old_logs(days_to_keep: int = 30):
    """Clean up old action logs"""
    db_path = os.getenv('DATABASE_PATH', 'basketball_bot.db')
    
    try:
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            
            # Delete logs older than specified days
            cursor.execute('''
                DELETE FROM action_logs 
                WHERE datetime(timestamp) < datetime('now', '-{} days')
            '''.format(days_to_keep))
            
            deleted_count = cursor.rowcount
            logger.info(f"Cleaned up {deleted_count} old log entries")
            return deleted_count
            
    except Exception as e:
        logger.error(f"Log cleanup failed: {e}")
        raise

async def get_database_stats():
    """Get database statistics"""
    db_path = os.getenv('DATABASE_PATH', 'basketball_bot.db')
    
    try:
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            
            # Get table sizes
            stats = {}
            
            cursor.execute("SELECT COUNT(*) FROM player_profiles")
            stats['total_profiles'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM action_logs")
            stats['total_logs'] = cursor.fetchone()[0]
            
            # Get database file size
            if os.path.exists(db_path):
                stats['db_size_bytes'] = os.path.getsize(db_path)
                stats['db_size_mb'] = round(stats['db_size_bytes'] / (1024 * 1024), 2)
            
            # Get most active users
            cursor.execute('''
                SELECT username, COUNT(*) as action_count
                FROM action_logs al
                JOIN player_profiles pp ON al.user_id = pp.user_id
                GROUP BY al.user_id, username
                ORDER BY action_count DESC
                LIMIT 5
            ''')
            stats['most_active_users'] = cursor.fetchall()
            
            return stats
            
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        return {}

def check_database_integrity():
    """Check database integrity"""
    db_path = os.getenv('DATABASE_PATH', 'basketball_bot.db')
    
    try:
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            
            # Run integrity check
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()[0]
            
            if result == "ok":
                logger.info("Database integrity check passed")
                return True
            else:
                logger.error(f"Database integrity check failed: {result}")
                return False
                
    except Exception as e:
        logger.error(f"Database integrity check error: {e}")
        return False

async def migrate_database():
    """Handle database migrations if needed"""
    db_path = os.getenv('DATABASE_PATH', 'basketball_bot.db')
    
    try:
        with DatabaseConnection(db_path) as conn:
            cursor = conn.cursor()
            
            # Check if we need to add new columns or tables
            cursor.execute("PRAGMA table_info(player_profiles)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # Example migration: add new column if it doesn't exist
            if 'last_active' not in columns:
                cursor.execute('''
                    ALTER TABLE player_profiles 
                    ADD COLUMN last_active TEXT DEFAULT NULL
                ''')
                logger.info("Added last_active column to player_profiles")
            
            # Update database version in settings
            cursor.execute('''
                INSERT OR REPLACE INTO bot_settings (key, value, updated_at)
                VALUES ('db_version', '1.0', datetime('now'))
            ''')
            
            logger.info("Database migration completed")
            
    except Exception as e:
        logger.error(f"Database migration failed: {e}")
        raise
