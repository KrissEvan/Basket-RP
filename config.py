import os
import json

# Basketball archetypes configuration
ARCHETYPES = {
    "Meneur": {
        "description": "Spécialisé dans la distribution et la vision de jeu",
        "stat_bonuses": {
            "Manip. Ballon": 15,
            "Agilité": 10,
            "Vitesse": 10,
            "Précision": 5,
            "Force Physique": -10,
            "Détente": -5
        },
        "position": "Guard"
    },
    "Arrière": {
        "description": "Excellent tireur avec une bonne vision défensive",
        "stat_bonuses": {
            "Précision": 15,
            "Défense": 10,
            "Vitesse": 5,
            "Agilité": 5,
            "Force Physique": -5,
            "Détente": -5
        },
        "position": "Guard"
    },
    "Ailier": {
        "description": "Joueur polyvalent, équilibré dans tous les domaines",
        "stat_bonuses": {
            "Agilité": 8,
            "Précision": 7,
            "Défense": 7,
            "Vitesse": 3,
            "Force Physique": -5
        },
        "position": "Forward"
    },
    "Ailier Fort": {
        "description": "Joueur physique avec un bon jeu près du panier",
        "stat_bonuses": {
            "Force Physique": 15,
            "Détente": 10,
            "Défense": 8,
            "Endurance": 2,
            "Vitesse": -10,
            "Agilité": -5
        },
        "position": "Forward"
    },
    "Pivot": {
        "description": "Dominant dans la raquette, excellent rebondeur",
        "stat_bonuses": {
            "Force Physique": 20,
            "Détente": 15,
            "Défense": 10,
            "Endurance": 5,
            "Vitesse": -15,
            "Agilité": -10,
            "Précision": -5
        },
        "position": "Center"
    },
    "Généraliste": {
        "description": "Aucune spécialisation, statistiques équilibrées",
        "stat_bonuses": {},
        "position": "Flexible"
    }
}

# Role-based archetype mapping (Discord role names to archetypes)
ROLE_ARCHETYPE_MAPPING = {
    "🏀 Meneur": "Meneur",
    "🎯 Arrière": "Arrière", 
    "⚡ Ailier": "Ailier",
    "💪 Ailier Fort": "Ailier Fort",
    "🏗️ Pivot": "Pivot",
    "🔄 Flex": "Généraliste"
}

# Admin role names that can use admin commands
ADMIN_ROLES = [
    "Modérateur",
    "Administrateur",
    "Coach",
    "Staff"
]

# Bot configuration
BOT_CONFIG = {
    "command_prefix": "!",
    "max_stat_value": 1000,
    "min_stat_value": 0,
    "base_stat_value": 500,
    "max_points_per_add": 100,
    "embed_color": 0xFF6B35,  # Orange basketball color
    "success_color": 0x00FF00,  # Green
    "error_color": 0xFF0000,   # Red
    "warning_color": 0xFFFF00  # Yellow
}

# Stat display configuration
STAT_EMOJIS = {
    "Force Physique": "💪",
    "Précision": "🎯", 
    "Manip. Ballon": "🏀",
    "Agilité": "⚡",
    "Détente": "🦘",
    "Défense": "🛡️",
    "Vitesse": "💨",
    "Endurance": "🔋"
}

STAT_ABBREVIATIONS = {
    "Force Physique": "FOR",
    "Précision": "PREC",
    "Manip. Ballon": "BALL",
    "Agilité": "AGI", 
    "Détente": "DET",
    "Défense": "DEF",
    "Vitesse": "VIT",
    "Endurance": "END"
}

def get_archetype_from_roles(member_roles):
    """Get archetype based on Discord member roles"""
    for role in member_roles:
        if role.name in ROLE_ARCHETYPE_MAPPING:
            return ROLE_ARCHETYPE_MAPPING[role.name]
    return "Généraliste"

def is_admin(member_roles, member=None):
    """Check if member has admin permissions"""
    # Check if user is server owner
    if member and hasattr(member, 'guild') and member.guild.owner_id == member.id:
        return True
    
    # Check for Discord admin permissions
    if member and hasattr(member, 'guild_permissions'):
        if member.guild_permissions.administrator:
            return True
        if member.guild_permissions.manage_guild:
            return True
    
    # Check for specific admin roles
    return any(role.name in ADMIN_ROLES for role in member_roles)

def get_stat_bar(value, max_value=1000):
    """Generate a visual stat bar"""
    filled = int((value / max_value) * 10)
    empty = 10 - filled
    return "█" * filled + "░" * empty

def validate_stat_name(stat_name):
    """Validate and normalize stat name"""
    # Check exact matches first
    if stat_name in STAT_EMOJIS:
        return stat_name
    
    # Check abbreviations
    for full_name, abbrev in STAT_ABBREVIATIONS.items():
        if stat_name.upper() == abbrev:
            return full_name
    
    # Check partial matches (case insensitive)
    stat_lower = stat_name.lower()
    for full_name in STAT_EMOJIS.keys():
        if stat_lower in full_name.lower():
            return full_name
    
    return None

# Color mapping for embed customization
COLOR_MAPPING = {
    "rouge": 0xFF0000,
    "red": 0xFF0000,
    "vert": 0x00FF00,
    "green": 0x00FF00,
    "bleu": 0x0000FF,
    "blue": 0x0000FF,
    "violet": 0x8A2BE2,
    "purple": 0x8A2BE2,
    "orange": 0xFF6B35,
    "jaune": 0xFFFF00,
    "yellow": 0xFFFF00,
    "rose": 0xFF69B4,
    "pink": 0xFF69B4,
    "noir": 0x000000,
    "black": 0x000000,
    "blanc": 0xFFFFFF,
    "white": 0xFFFFFF,
    "cyan": 0x00FFFF,
    "magenta": 0xFF00FF,
    "basketball": 0xFF6B35  # Orange basketball par défaut
}

def get_color_from_name(color_name: str) -> int:
    """Get color hex from name"""
    return COLOR_MAPPING.get(color_name.lower(), BOT_CONFIG["embed_color"])

# Environment variables
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN', 'your_discord_token_here')
DATABASE_PATH = os.getenv('DATABASE_PATH', 'basketball_bot.db')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
