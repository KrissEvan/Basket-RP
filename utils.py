import discord
from config import BOT_CONFIG
import asyncio
from typing import List, Optional

def create_embed(title: str, description: str, color: int = 0xFF6B35) -> discord.Embed:
    """Create a standardized embed"""
    if color is None:
        color = BOT_CONFIG["embed_color"]
    
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    return embed

def create_success_embed(title: str, description: str) -> discord.Embed:
    """Create a success embed"""
    return create_embed(title, description, BOT_CONFIG["success_color"])

def create_error_embed(title: str, description: str) -> discord.Embed:
    """Create an error embed"""
    return create_embed(title, description, BOT_CONFIG["error_color"])

def create_warning_embed(title: str, description: str) -> discord.Embed:
    """Create a warning embed"""
    return create_embed(title, description, BOT_CONFIG["warning_color"])

async def send_paginated_embed(ctx, embeds: List[discord.Embed], timeout: int = 60):
    """Send multiple embeds with pagination using reactions"""
    if not embeds:
        return
    
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
        return
    
    current_page = 0
    message = await ctx.send(embed=embeds[current_page])
    
    # Add reaction controls
    await message.add_reaction("⬅️")
    await message.add_reaction("➡️")
    await message.add_reaction("❌")
    
    def check(reaction, user):
        return (
            user == ctx.author and 
            str(reaction.emoji) in ["⬅️", "➡️", "❌"] and 
            reaction.message.id == message.id
        )
    
    while True:
        try:
            reaction, user = await ctx.bot.wait_for("reaction_add", timeout=timeout, check=check)
            
            if str(reaction.emoji) == "➡️" and current_page < len(embeds) - 1:
                current_page += 1
                await message.edit(embed=embeds[current_page])
            elif str(reaction.emoji) == "⬅️" and current_page > 0:
                current_page -= 1
                await message.edit(embed=embeds[current_page])
            elif str(reaction.emoji) == "❌":
                await message.delete()
                return
            
            await message.remove_reaction(reaction, user)
            
        except asyncio.TimeoutError:
            try:
                await message.clear_reactions()
            except discord.Forbidden:
                pass
            break

def format_stat_value(value: int, max_value: int = 100) -> str:
    """Format a stat value with color coding"""
    percentage = (value / max_value) * 100
    
    if percentage >= 90:
        return f"**{value}** 🔥"  # Excellent
    elif percentage >= 75:
        return f"**{value}** ⭐"  # Very good
    elif percentage >= 60:
        return f"**{value}** ✅"  # Good
    elif percentage >= 40:
        return f"**{value}** ⚠️"   # Average
    else:
        return f"**{value}** ❌"   # Poor

def calculate_overall_rating(stats: dict) -> tuple:
    """Calculate overall player rating and grade"""
    total = sum(stats.values())
    average = total / len(stats)
    
    if average >= 85:
        grade = "S"
        rating = "Elite"
    elif average >= 75:
        grade = "A"
        rating = "Excellent"
    elif average >= 65:
        grade = "B"
        rating = "Très bon"
    elif average >= 55:
        grade = "C"
        rating = "Bon"
    elif average >= 45:
        grade = "D"
        rating = "Moyen"
    else:
        grade = "F"
        rating = "Faible"
    
    return grade, rating, round(average, 1)

def get_position_from_stats(stats: dict) -> str:
    """Suggest best position based on stats"""
    # Calculate position scores
    point_guard_score = (stats["Manip. Ballon"] + stats["Agilité"] + stats["Vitesse"]) / 3
    shooting_guard_score = (stats["Précision"] + stats["Défense"] + stats["Vitesse"]) / 3
    small_forward_score = (stats["Agilité"] + stats["Précision"] + stats["Défense"]) / 3
    power_forward_score = (stats["Force Physique"] + stats["Détente"] + stats["Défense"]) / 3
    center_score = (stats["Force Physique"] + stats["Détente"] + stats["Endurance"]) / 3
    
    positions = {
        "Meneur": point_guard_score,
        "Arrière": shooting_guard_score,
        "Ailier": small_forward_score,
        "Ailier Fort": power_forward_score,
        "Pivot": center_score
    }
    
    return max(positions.keys(), key=lambda x: positions[x])

async def confirm_action(ctx, message: str, timeout: int = 30) -> bool:
    """Ask for user confirmation with reactions"""
    embed = create_warning_embed("⚠️ Confirmation requise", message)
    confirmation = await ctx.send(embed=embed)
    
    await confirmation.add_reaction("✅")
    await confirmation.add_reaction("❌")
    
    def check(reaction, user):
        return (
            user == ctx.author and 
            str(reaction.emoji) in ["✅", "❌"] and 
            reaction.message.id == confirmation.id
        )
    
    try:
        reaction, user = await ctx.bot.wait_for("reaction_add", timeout=timeout, check=check)
        await confirmation.delete()
        return str(reaction.emoji) == "✅"
    except asyncio.TimeoutError:
        await confirmation.delete()
        return False

def validate_points_distribution(stats: dict, available_points: int, max_stat: int = 100) -> tuple:
    """Validate if points distribution is valid"""
    errors = []
    
    # Check if any stat exceeds maximum
    for stat_name, value in stats.items():
        if value > max_stat:
            errors.append(f"{stat_name} ne peut pas dépasser {max_stat}")
    
    # Check if total points used exceeds available
    base_total = 50 * len(stats)  # Base 50 for each stat
    current_total = sum(stats.values())
    points_used = current_total - base_total
    
    if points_used > available_points:
        errors.append(f"Vous utilisez {points_used} points mais n'en avez que {available_points}")
    
    return len(errors) == 0, errors

def get_stat_recommendations(archetype: str) -> dict:
    """Get stat recommendations for an archetype"""
    recommendations = {
        "Meneur": {
            "primary": ["Manip. Ballon", "Agilité", "Vitesse"],
            "secondary": ["Précision", "Endurance"],
            "avoid": ["Force Physique"]
        },
        "Arrière": {
            "primary": ["Précision", "Défense", "Vitesse"],
            "secondary": ["Agilité", "Manip. Ballon"],
            "avoid": ["Force Physique"]
        },
        "Ailier": {
            "primary": ["Agilité", "Précision", "Défense"],
            "secondary": ["Vitesse", "Manip. Ballon"],
            "avoid": []
        },
        "Ailier Fort": {
            "primary": ["Force Physique", "Détente", "Défense"],
            "secondary": ["Endurance", "Précision"],
            "avoid": ["Vitesse", "Agilité"]
        },
        "Pivot": {
            "primary": ["Force Physique", "Détente", "Défense"],
            "secondary": ["Endurance"],
            "avoid": ["Vitesse", "Agilité", "Manip. Ballon"]
        },
        "Généraliste": {
            "primary": [],
            "secondary": list(stats for stats in ["Force Physique", "Précision", "Manip. Ballon", "Agilité", "Détente", "Défense", "Vitesse", "Endurance"]),
            "avoid": []
        }
    }
    
    return recommendations.get(archetype, recommendations["Généraliste"])
