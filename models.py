import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, Any

class PlayerProfile:
    """Model for player basketball profiles"""
    
    def __init__(self, user_id: int, username: str, archetype: str = "Généraliste"):
        self.user_id = user_id
        self.username = username
        self.archetype = archetype
        self.stats = {
            "Force Physique": 500,
            "Précision": 500,
            "Manip. Ballon": 500,
            "Agilité": 500,
            "Détente": 500,
            "Défense": 500,
            "Vitesse": 500,
            "Endurance": 500
        }
        self.available_points = 0
        # Informations personnalisables
        self.character_name = ""
        self.first_name = ""
        self.age = 0
        self.height = 0  # cm, modifiable par admin
        self.weight = 0  # kg, modifiable par admin
        self.profile_image = ""
        self.embed_color = 0xFF6B35  # Couleur par défaut
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def apply_archetype_bonus(self, archetype_config: Dict[str, Any]):
        """Apply archetype bonuses to base stats"""
        if self.archetype in archetype_config:
            bonuses = archetype_config[self.archetype].get("stat_bonuses", {})
            for stat, bonus in bonuses.items():
                if stat in self.stats:
                    self.stats[stat] = max(0, min(100, self.stats[stat] + bonus))
    
    def add_stat_points(self, stat: str, points: int) -> bool:
        """Add points to a specific stat"""
        if stat not in self.stats:
            return False
        
        if points < 0 or points > self.available_points:
            return False
        
        new_value = self.stats[stat] + points
        if new_value > 1000:
            return False
        
        self.stats[stat] = new_value
        self.available_points -= points
        self.updated_at = datetime.now()
        return True
    
    def get_total_stats(self) -> int:
        """Get total sum of all stats"""
        return sum(self.stats.values())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary for database storage"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "archetype": self.archetype,
            "stats": json.dumps(self.stats),
            "available_points": self.available_points,
            "character_name": self.character_name,
            "first_name": self.first_name,
            "age": self.age,
            "height": self.height,
            "weight": self.weight,
            "profile_image": self.profile_image,
            "embed_color": self.embed_color,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlayerProfile':
        """Create profile from dictionary data"""
        profile = cls(data["user_id"], data["username"], data["archetype"])
        profile.stats = json.loads(data["stats"])
        profile.available_points = data["available_points"]
        profile.character_name = data.get("character_name", "")
        profile.first_name = data.get("first_name", "")
        profile.age = data.get("age", 0)
        profile.height = data.get("height", 0)
        profile.weight = data.get("weight", 0)
        profile.profile_image = data.get("profile_image", "")
        profile.embed_color = data.get("embed_color", 0xFF6B35)
        profile.created_at = datetime.fromisoformat(data["created_at"])
        profile.updated_at = datetime.fromisoformat(data["updated_at"])
        return profile

class DatabaseManager:
    """Database manager for player profiles"""
    
    def __init__(self, db_path: str = "basketball_bot.db"):
        self.db_path = db_path
        self.init_tables()
    
    def init_tables(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS player_profiles (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL,
                    archetype TEXT NOT NULL,
                    stats TEXT NOT NULL,
                    available_points INTEGER DEFAULT 0,
                    character_name TEXT DEFAULT "",
                    first_name TEXT DEFAULT "",
                    age INTEGER DEFAULT 0,
                    height INTEGER DEFAULT 0,
                    weight INTEGER DEFAULT 0,
                    profile_image TEXT DEFAULT "",
                    embed_color INTEGER DEFAULT 16742965,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS action_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT,
                    admin_id INTEGER,
                    timestamp TEXT NOT NULL
                )
            ''')
            conn.commit()
    
    def save_profile(self, profile: PlayerProfile) -> bool:
        """Save or update a player profile"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                data = profile.to_dict()
                cursor.execute('''
                    INSERT OR REPLACE INTO player_profiles 
                    (user_id, username, archetype, stats, available_points, character_name, first_name, age, height, weight, profile_image, embed_color, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data["user_id"], data["username"], data["archetype"], 
                    data["stats"], data["available_points"], data["character_name"],
                    data["first_name"], data["age"], data["height"], data["weight"],
                    data["profile_image"], data["embed_color"],
                    data["created_at"], data["updated_at"]
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error saving profile: {e}")
            return False
    
    def get_profile(self, user_id: int) -> Optional[PlayerProfile]:
        """Get a player profile by user ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, username, archetype, stats, available_points, character_name, first_name, age, height, weight, profile_image, embed_color, created_at, updated_at
                    FROM player_profiles WHERE user_id = ?
                ''', (user_id,))
                
                row = cursor.fetchone()
                if row:
                    data = {
                        "user_id": row[0],
                        "username": row[1],
                        "archetype": row[2],
                        "stats": row[3],
                        "available_points": row[4],
                        "character_name": row[5],
                        "first_name": row[6],
                        "age": row[7],
                        "height": row[8],
                        "weight": row[9],
                        "profile_image": row[10],
                        "embed_color": row[11],
                        "created_at": row[12],
                        "updated_at": row[13]
                    }
                    return PlayerProfile.from_dict(data)
                return None
        except Exception as e:
            print(f"Error getting profile: {e}")
            return None
    def delete_profile(self, user_id: int) -> bool:
        """Delete a player profile"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM player_profiles WHERE user_id = ?", (user_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting profile: {e}")
            return False
    
    def log_action(self, user_id: int, action: str, details: str = "", admin_id: int = 0):
        """Log an action to the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO action_logs (user_id, action, details, admin_id, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, action, details, admin_id, datetime.now().isoformat()))
                conn.commit()
        except Exception as e:
            print(f"Error logging action: {e}")
    
    def get_all_profiles(self) -> list:
        """Get all player profiles"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, username, archetype, stats, available_points, character_name, first_name, age, height, weight, profile_image, embed_color, created_at, updated_at
                    FROM player_profiles ORDER BY username
                ''')
                
                profiles = []
                for row in cursor.fetchall():
                    data = {
                        "user_id": row[0],
                        "username": row[1],
                        "archetype": row[2],
                        "stats": row[3],
                        "available_points": row[4],
                        "character_name": row[5],
                        "first_name": row[6],
                        "age": row[7],
                        "height": row[8],
                        "weight": row[9],
                        "profile_image": row[10],
                        "embed_color": row[11],
                        "created_at": row[12],
                        "updated_at": row[13]
                    }
                    profiles.append(PlayerProfile.from_dict(data))
                return profiles
        except Exception as e:
            print(f"Error getting all profiles: {e}")
            return []
