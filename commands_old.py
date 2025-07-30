import discord
from discord.ext import commands
from models import DatabaseManager, PlayerProfile
from config import (
    ARCHETYPES, BOT_CONFIG, STAT_EMOJIS, STAT_ABBREVIATIONS,
    get_archetype_from_roles, is_admin, get_stat_bar, validate_stat_name,
    COLOR_MAPPING, get_color_from_name
)
import logging
from typing import Optional

logger = logging.getLogger(__name__)
db_manager = DatabaseManager()

async def setup_commands(bot):
    """Setup all bot commands"""
    
    # Load slash command modules
    try:
        await bot.load_extension('basic_commands')
        logger.info("Loaded slash commands")
    except Exception as e:
        logger.error(f"Failed to load slash commands: {e}")
    
    try:
        await bot.load_extension('admin_commands')
        logger.info("Loaded admin commands")
    except Exception as e:
        logger.error(f"Failed to load admin commands: {e}")
    
    @bot.command(name='profil', aliases=['profile', 'p'])
    async def show_profile(ctx, member: Optional[discord.Member] = None):
        """Afficher le profil d'un joueur"""
        target = member or ctx.author
        profile = db_manager.get_profile(target.id)
        
        if not profile:
            if target == ctx.author:
                embed = discord.Embed(
                    title="❌ Profil introuvable",
                    description="Vous n'avez pas encore de profil. Utilisez `!create` pour en créer un.",
                    color=BOT_CONFIG["error_color"]
                )
            else:
                embed = discord.Embed(
                    title="❌ Profil introuvable", 
                    description=f"{target.display_name} n'a pas de profil créé.",
                    color=BOT_CONFIG["error_color"]
                )
            await ctx.send(embed=embed)
            return
        
        # Create profile embed
        embed = discord.Embed(
            title=f"🏀 Profil de {profile.username}",
            description=f"**Archétype:** {profile.archetype}\n**Points disponibles:** {profile.available_points}",
            color=BOT_CONFIG["embed_color"]
        )
        
        # Add character info if available
        if profile.character_name or profile.first_name or profile.age:
            character_info = ""
            if profile.character_name:
                character_info += f"**Nom:** {profile.character_name}\n"
            if profile.first_name:
                character_info += f"**Prénom:** {profile.first_name}\n"
            if profile.age > 0:
                character_info += f"**Âge:** {profile.age} ans\n"
            if profile.height > 0:
                character_info += f"**Taille:** {profile.height} cm\n"
            if profile.weight > 0:
                character_info += f"**Poids:** {profile.weight} kg\n"
            embed.add_field(name="👤 Informations du personnage", value=character_info, inline=True)

        # Add stats field
        stats_text = ""
        for stat_name, value in profile.stats.items():
            emoji = STAT_EMOJIS.get(stat_name, "📊")
            bar = get_stat_bar(value)
            stats_text += f"{emoji} **{stat_name}:** {value}/1000\n`{bar}`\n"
        
        embed.add_field(name="📈 Statistiques", value=stats_text, inline=False)
        
        # Add archetype description
        if profile.archetype in ARCHETYPES:
            archetype_info = ARCHETYPES[profile.archetype]
            embed.add_field(
                name="📋 Description de l'archétype",
                value=archetype_info["description"],
                inline=False
            )
        
        # Add total stats
        total_stats = profile.get_total_stats()
        embed.add_field(name="🎯 Total des stats", value=f"{total_stats}/8000", inline=True)
        
        # Set custom embed color if available
        if hasattr(profile, 'embed_color') and profile.embed_color:
            embed.color = profile.embed_color
        
        # Add profile image if available
        if hasattr(profile, 'profile_image') and profile.profile_image:
            embed.set_thumbnail(url=profile.profile_image)
        
        # Add footer
        embed.set_footer(text=f"Profil créé le {profile.created_at.strftime('%d/%m/%Y')}")
        
        await ctx.send(embed=embed)
    
    @bot.command(name='create', aliases=['creer'])
    async def create_profile(ctx):
        """Créer un nouveau profil de joueur"""
        # Check if profile already exists
        existing_profile = db_manager.get_profile(ctx.author.id)
        if existing_profile:
            embed = discord.Embed(
                title="❌ Profil existant",
                description="Vous avez déjà un profil. Utilisez `!profil` pour le voir.",
                color=BOT_CONFIG["error_color"]
            )
            await ctx.send(embed=embed)
            return
        
        # Determine archetype from roles
        archetype = get_archetype_from_roles(ctx.author.roles)
        
        # Create new profile
        profile = PlayerProfile(ctx.author.id, ctx.author.display_name, archetype)
        profile.apply_archetype_bonus(ARCHETYPES)
        profile.available_points = 200  # Starting points for new players (adjusted for 1000 max)
        
        # Save profile
        if db_manager.save_profile(profile):
            db_manager.log_action(ctx.author.id, "PROFILE_CREATED", f"Archetype: {archetype}")
            
            embed = discord.Embed(
                title="✅ Profil créé avec succès!",
                description=f"Votre profil a été créé avec l'archétype **{archetype}**.",
                color=BOT_CONFIG["success_color"]
            )
            
            # Show archetype bonuses
            if archetype in ARCHETYPES and ARCHETYPES[archetype]["stat_bonuses"]:
                bonuses_text = ""
                for stat, bonus in ARCHETYPES[archetype]["stat_bonuses"].items():
                    emoji = STAT_EMOJIS.get(stat, "📊")
                    sign = "+" if bonus > 0 else ""
                    bonuses_text += f"{emoji} {stat}: {sign}{bonus}\n"
                
                embed.add_field(name="🎯 Bonus d'archétype appliqués", value=bonuses_text, inline=False)
            
            embed.add_field(
                name="🎁 Points de départ", 
                value=f"Vous avez reçu **{profile.available_points} points** à répartir!\nUtilisez `!add <stat> <points>` pour les distribuer.",
                inline=False
            )
            
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Erreur de création",
                description="Une erreur s'est produite lors de la création de votre profil.",
                color=BOT_CONFIG["error_color"]
            )
            await ctx.send(embed=embed)
    
    @bot.command(name='add', aliases=['ajouter'])
    async def add_stat_points(ctx, stat_name: str, points: int):
        """Ajouter des points à une statistique"""
        # Get player profile
        profile = db_manager.get_profile(ctx.author.id)
        if not profile:
            embed = discord.Embed(
                title="❌ Profil introuvable",
                description="Vous devez créer un profil avant d'ajouter des points. Utilisez `!create`.",
                color=BOT_CONFIG["error_color"]
            )
            await ctx.send(embed=embed)
            return
        
        # Validate stat name
        validated_stat = validate_stat_name(stat_name)
        if not validated_stat:
            available_stats = ", ".join([f"{abbrev}" for abbrev in STAT_ABBREVIATIONS.values()])
            embed = discord.Embed(
                title="❌ Statistique invalide",
                description=f"Statistique non reconnue: `{stat_name}`\n\n**Stats disponibles:**\n{available_stats}",
                color=BOT_CONFIG["error_color"]
            )
            await ctx.send(embed=embed)
            return
        
        # Validate points
        if points <= 0:
            embed = discord.Embed(
                title="❌ Points invalides",
                description="Vous devez ajouter au moins 1 point.",
                color=BOT_CONFIG["error_color"]
            )
            await ctx.send(embed=embed)
            return
        
        if points > BOT_CONFIG["max_points_per_add"]:
            embed = discord.Embed(
                title="❌ Trop de points",
                description=f"Vous ne pouvez pas ajouter plus de {BOT_CONFIG['max_points_per_add']} points à la fois.",
                color=BOT_CONFIG["error_color"]
            )
            await ctx.send(embed=embed)
            return
        
        if points > profile.available_points:
            embed = discord.Embed(
                title="❌ Points insuffisants",
                description=f"Vous n'avez que {profile.available_points} points disponibles.",
                color=BOT_CONFIG["error_color"]
            )
            await ctx.send(embed=embed)
            return
        
        current_stat = profile.stats[validated_stat]
        if current_stat + points > BOT_CONFIG["max_stat_value"]:
            max_addable = BOT_CONFIG["max_stat_value"] - current_stat
            embed = discord.Embed(
                title="❌ Limite de stat atteinte",
                description=f"Vous ne pouvez ajouter que {max_addable} points maximum à {validated_stat} (actuellement {current_stat}/1000).",
                color=BOT_CONFIG["error_color"]
            )
            await ctx.send(embed=embed)
            return
        
        # Add points
        if profile.add_stat_points(validated_stat, points):
            if db_manager.save_profile(profile):
                db_manager.log_action(
                    ctx.author.id, 
                    "POINTS_ADDED", 
                    f"{points} points added to {validated_stat}"
                )
                
                emoji = STAT_EMOJIS.get(validated_stat, "📊")
                new_value = profile.stats[validated_stat]
                embed = discord.Embed(
                    title="✅ Points ajoutés!",
                    description=f"{emoji} **{validated_stat}**: {current_stat} → **{new_value}** (+{points})",
                    color=BOT_CONFIG["success_color"]
                )
                embed.add_field(
                    name="Points restants", 
                    value=f"{profile.available_points} points",
                    inline=True
                )
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="❌ Erreur de sauvegarde",
                    description="Une erreur s'est produite lors de la sauvegarde.",
                    color=BOT_CONFIG["error_color"]
                )
                await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Erreur",
                description="Impossible d'ajouter les points.",
                color=BOT_CONFIG["error_color"]
            )
            await ctx.send(embed=embed)
    
    @bot.command(name='givepoints', aliases=['donner'])
    @commands.has_permissions(manage_roles=True)
    async def give_points(ctx, member: discord.Member, points: int):
        """[ADMIN] Donner des points à un joueur"""
        # Check admin permissions
        if not is_admin(ctx.author.roles):
            embed = discord.Embed(
                title="❌ Permission refusée",
                description="Vous n'avez pas les permissions pour utiliser cette commande.",
                color=BOT_CONFIG["error_color"]
            )
            await ctx.send(embed=embed)
            return
        
        # Get target profile
        profile = db_manager.get_profile(member.id)
        if not profile:
            embed = discord.Embed(
                title="❌ Profil introuvable",
                description=f"{member.display_name} n'a pas de profil créé.",
                color=BOT_CONFIG["error_color"]
            )
            await ctx.send(embed=embed)
            return
        
        # Validate points
        if points <= 0:
            embed = discord.Embed(
                title="❌ Points invalides",
                description="Le nombre de points doit être positif.",
                color=BOT_CONFIG["error_color"]
            )
            await ctx.send(embed=embed)
            return
        
        # Add points
        profile.available_points += points
        
        if db_manager.save_profile(profile):
            db_manager.log_action(
                member.id, 
                "POINTS_GIVEN", 
                f"{points} points given by admin",
                ctx.author.id
            )
            
            embed = discord.Embed(
                title="✅ Points attribués!",
                description=f"**{points} points** ont été donnés à {member.display_name}.",
                color=BOT_CONFIG["success_color"]
            )
            embed.add_field(
                name="Nouveaux points disponibles",
                value=f"{profile.available_points} points",
                inline=True
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Erreur de sauvegarde",
                description="Une erreur s'est produite lors de la sauvegarde.",
                color=BOT_CONFIG["error_color"]
            )
            await ctx.send(embed=embed)
    
    @bot.command(name='archetypes', aliases=['archetype'])
    async def show_archetypes(ctx):
        """Afficher la liste des archétypes disponibles"""
        embed = discord.Embed(
            title="🏀 Archétypes de Basketball",
            description="Voici les différents archétypes disponibles et leurs bonus de stats:",
            color=BOT_CONFIG["embed_color"]
        )
        
        for archetype_name, archetype_data in ARCHETYPES.items():
            bonuses_text = archetype_data["description"] + "\n\n"
            
            if archetype_data["stat_bonuses"]:
                bonuses_text += "**Modifications de stats:**\n"
                for stat, bonus in archetype_data["stat_bonuses"].items():
                    emoji = STAT_EMOJIS.get(stat, "📊")
                    sign = "+" if bonus > 0 else ""
                    bonuses_text += f"{emoji} {stat}: {sign}{bonus}\n"
            else:
                bonuses_text += "**Aucune modification de stats**"
            
            embed.add_field(
                name=f"**{archetype_name}** ({archetype_data['position']})",
                value=bonuses_text,
                inline=True
            )
        
        embed.set_footer(text="L'archétype est automatiquement attribué selon vos rôles Discord")
        await ctx.send(embed=embed)
    
    @bot.command(name='stats', aliases=['statistiques'])
    async def show_stats_info(ctx):
        """Afficher des informations sur les statistiques"""
        embed = discord.Embed(
            title="📊 Guide des Statistiques",
            description="Voici la description de chaque statistique et son abréviation:",
            color=BOT_CONFIG["embed_color"]
        )
        
        stat_descriptions = {
            "Force Physique": "Puissance physique et présence sous les paniers",
            "Précision": "Précision des tirs et des passes",
            "Manip. Ballon": "Habileté avec le ballon et dribbles",
            "Agilité": "Capacité à changer de direction rapidement",
            "Détente": "Capacité de saut et jeu aérien",
            "Défense": "Qualités défensives et interceptions",
            "Vitesse": "Rapidité de déplacement sur le terrain",
            "Endurance": "Résistance physique et récupération"
        }
        
        for stat_name, description in stat_descriptions.items():
            emoji = STAT_EMOJIS.get(stat_name, "📊")
            abbrev = STAT_ABBREVIATIONS.get(stat_name, "")
            embed.add_field(
                name=f"{emoji} {stat_name} ({abbrev})",
                value=description,
                inline=True
            )
        
        embed.add_field(
            name="💡 Conseils",
            value="• Toutes les stats vont de 0 à 100\n• Utilisez les abréviations pour les commandes\n• Votre archétype influence vos stats de base",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @bot.command(name='leaderboard', aliases=['classement', 'top'])
    async def show_leaderboard(ctx, stat: str = ""):
        """Afficher le classement des joueurs"""
        profiles = db_manager.get_all_profiles()
        
        if not profiles:
            embed = discord.Embed(
                title="📋 Classement vide",
                description="Aucun profil n'a été créé pour le moment.",
                color=BOT_CONFIG["warning_color"]
            )
            await ctx.send(embed=embed)
            return
        
        if stat and stat.strip():
            # Specific stat leaderboard
            validated_stat = validate_stat_name(stat)
            if not validated_stat:
                embed = discord.Embed(
                    title="❌ Statistique invalide",
                    description=f"Statistique non reconnue: `{stat}`",
                    color=BOT_CONFIG["error_color"]
                )
                await ctx.send(embed=embed)
                return
            
            # Sort by specific stat
            profiles.sort(key=lambda p: p.stats[validated_stat], reverse=True)
            emoji = STAT_EMOJIS.get(validated_stat, "📊")
            
            embed = discord.Embed(
                title=f"🏆 Classement - {emoji} {validated_stat}",
                color=BOT_CONFIG["embed_color"]
            )
            
            leaderboard_text = ""
            for i, profile in enumerate(profiles[:10], 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                stat_value = profile.stats[validated_stat]
                leaderboard_text += f"{medal} **{profile.username}** - {stat_value}/1000\n"
            
            embed.description = leaderboard_text
            
        else:
            # Overall leaderboard (total stats)
            profiles.sort(key=lambda p: p.get_total_stats(), reverse=True)
            
            embed = discord.Embed(
                title="🏆 Classement Général",
                description="Classement par total de statistiques",
                color=BOT_CONFIG["embed_color"]
            )
            
            leaderboard_text = ""
            for i, profile in enumerate(profiles[:10], 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                total_stats = profile.get_total_stats()
                leaderboard_text += f"{medal} **{profile.username}** ({profile.archetype}) - {total_stats}/8000\n"
            
            embed.description = leaderboard_text
        
        embed.set_footer(text=f"Total des joueurs: {len(profiles)}")
        await ctx.send(embed=embed)



    @bot.command(name='customize', aliases=['personnaliser', 'custom'])
    async def customize_profile(ctx, field: str = "", *, value: str = ""):
        """Personnaliser son profil (nom, prénom, âge, image)"""
        profile = db_manager.get_profile(ctx.author.id)
        if not profile:
            embed = discord.Embed(
                title="❌ Profil introuvable",
                description="Vous devez créer un profil avant de le personnaliser. Utilisez `!create`.",
                color=BOT_CONFIG["error_color"]
            )
            await ctx.send(embed=embed)
            return
        
        if not field:
            embed = discord.Embed(
                title="🎨 Personnalisation du profil",
                description="Utilisez cette commande pour personnaliser votre profil :",
                color=BOT_CONFIG["embed_color"]
            )
            embed.add_field(
                name="Commandes disponibles",
                value="`!customize nom <votre nom>`\n`!customize prénom <votre prénom>`\n`!customize âge <votre âge>`\n`!customize image <URL de votre image>`",
                inline=False
            )
            await ctx.send(embed=embed)
            return
        
        from datetime import datetime
        field_lower = field.lower()
        if field_lower in ["nom", "name"]:
            profile.character_name = value
            field_name = "nom"
        elif field_lower in ["prénom", "prenom", "firstname"]:
            profile.first_name = value
            field_name = "prénom"
        elif field_lower in ["âge", "age"]:
            try:
                profile.age = int(value)
                field_name = "âge"
            except ValueError:
                embed = discord.Embed(
                    title="❌ Âge invalide",
                    description="L'âge doit être un nombre entier.",
                    color=BOT_CONFIG["error_color"]
                )
                await ctx.send(embed=embed)
                return
        elif field_lower in ["image", "photo", "avatar"]:
            profile.profile_image = value
            field_name = "image"
        else:
            embed = discord.Embed(
                title="❌ Champ invalide",
                description="Champs disponibles : nom, prénom, âge, image",
                color=BOT_CONFIG["error_color"]
            )
            await ctx.send(embed=embed)
            return
        
        profile.updated_at = datetime.now()
        if db_manager.save_profile(profile):
            db_manager.log_action(ctx.author.id, "PROFILE_CUSTOMIZED", f"{field_name} updated")
            embed = discord.Embed(
                title="✅ Profil mis à jour !",
                description=f"Votre {field_name} a été mis à jour avec succès.",
                color=BOT_CONFIG["success_color"]
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Erreur de sauvegarde",
                description="Une erreur s'est produite lors de la sauvegarde.",
                color=BOT_CONFIG["error_color"]
            )
            await ctx.send(embed=embed)

    @bot.command(name='setphysical', aliases=['physical'])
    @commands.has_permissions(manage_roles=True)
    async def set_physical_stats(ctx, member: discord.Member, height: int = 0, weight: int = 0):
        """[ADMIN] Définir la taille et le poids d'un joueur"""
        if not is_admin(ctx.author.roles):
            embed = discord.Embed(
                title="❌ Permission refusée",
                description="Vous n'avez pas les permissions pour utiliser cette commande.",
                color=BOT_CONFIG["error_color"]
            )
            await ctx.send(embed=embed)
            return
        
        profile = db_manager.get_profile(member.id)
        if not profile:
            embed = discord.Embed(
                title="❌ Profil introuvable",
                description=f"{member.display_name} n'a pas de profil créé.",
                color=BOT_CONFIG["error_color"]
            )
            await ctx.send(embed=embed)
            return
        
        from datetime import datetime
        if height > 0:
            profile.height = height
        if weight > 0:
            profile.weight = weight
        
        profile.updated_at = datetime.now()
        if db_manager.save_profile(profile):
            db_manager.log_action(member.id, "PHYSICAL_STATS_SET", f"Height: {height}cm, Weight: {weight}kg", ctx.author.id)
            embed = discord.Embed(
                title="✅ Statistiques physiques mises à jour !",
                description=f"Profil de {member.display_name} mis à jour :\n**Taille :** {height} cm\n**Poids :** {weight} kg",
                color=BOT_CONFIG["success_color"]
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Erreur de sauvegarde",
                description="Une erreur s'est produite lors de la sauvegarde.",
                color=BOT_CONFIG["error_color"]
            )
            await ctx.send(embed=embed)

    @bot.command(name='deleteprofile', aliases=['supprimer', 'delete'])
    @commands.has_permissions(manage_roles=True)
    async def delete_profile(ctx, member: discord.Member):
        """[ADMIN] Supprimer le profil d'un joueur"""
        if not is_admin(ctx.author.roles):
            embed = discord.Embed(
                title="❌ Permission refusée",
                description="Vous n'avez pas les permissions pour utiliser cette commande.",
                color=BOT_CONFIG["error_color"]
            )
            await ctx.send(embed=embed)
            return
        
        profile = db_manager.get_profile(member.id)
        if not profile:
            embed = discord.Embed(
                title="❌ Profil introuvable",
                description=f"{member.display_name} n'a pas de profil créé.",
                color=BOT_CONFIG["error_color"]
            )
            await ctx.send(embed=embed)
            return
        
        # Confirmation
        confirm_embed = discord.Embed(
            title="⚠️ Confirmation de suppression",
            description=f"Êtes-vous sûr de vouloir supprimer le profil de **{member.display_name}** ?\n\nCette action est **irréversible** !",
            color=BOT_CONFIG["warning_color"]
        )
        confirmation = await ctx.send(embed=confirm_embed)
        await confirmation.add_reaction("✅")
        await confirmation.add_reaction("❌")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirmation.id
        
        try:
            reaction, user = await bot.wait_for("reaction_add", timeout=30, check=check)
            if str(reaction.emoji) == "✅":
                if db_manager.delete_profile(member.id):
                    db_manager.log_action(member.id, "PROFILE_DELETED", "Profile deleted by admin", ctx.author.id)
                    embed = discord.Embed(
                        title="✅ Profil supprimé",
                        description=f"Le profil de {member.display_name} a été supprimé avec succès.",
                        color=BOT_CONFIG["success_color"]
                    )
                else:
                    embed = discord.Embed(
                        title="❌ Erreur de suppression",
                        description="Une erreur s'est produite lors de la suppression.",
                        color=BOT_CONFIG["error_color"]
                    )
            else:
                embed = discord.Embed(
                    title="❌ Suppression annulée",
                    description="La suppression du profil a été annulée.",
                    color=BOT_CONFIG["warning_color"]
                )
            await confirmation.delete()
            await ctx.send(embed=embed)
        except Exception:
            await confirmation.delete()
            embed = discord.Embed(
                title="❌ Temps écoulé",
                description="La suppression a été annulée (temps écoulé).",
                color=BOT_CONFIG["error_color"]
            )
            await ctx.send(embed=embed)

    @bot.command(name='color', aliases=['couleur'])
    async def set_embed_color(ctx, color_name: str = ""):
        """Changer la couleur de son profil"""
        profile = db_manager.get_profile(ctx.author.id)
        if not profile:
            embed = discord.Embed(
                title="❌ Profil introuvable",
                description="Vous devez créer un profil avant de changer la couleur. Utilisez `!create`.",
                color=BOT_CONFIG["error_color"]
            )
            await ctx.send(embed=embed)
            return
        
        if not color_name:
            available_colors = ", ".join(COLOR_MAPPING.keys())
            embed = discord.Embed(
                title="🎨 Couleurs disponibles",
                description=f"Utilisez `!color <couleur>` avec une des couleurs suivantes :\n\n{available_colors}",
                color=BOT_CONFIG["embed_color"]
            )
            await ctx.send(embed=embed)
            return
        
        new_color = get_color_from_name(color_name)
        if new_color == BOT_CONFIG["embed_color"] and color_name.lower() not in COLOR_MAPPING:
            embed = discord.Embed(
                title="❌ Couleur inconnue",
                description=f"Couleur `{color_name}` non reconnue. Utilisez `!color` pour voir les couleurs disponibles.",
                color=BOT_CONFIG["error_color"]
            )
            await ctx.send(embed=embed)
            return
        
        from datetime import datetime
        profile.embed_color = new_color
        profile.updated_at = datetime.now()
        
        if db_manager.save_profile(profile):
            db_manager.log_action(ctx.author.id, "COLOR_CHANGED", f"Color changed to {color_name}")
            embed = discord.Embed(
                title="✅ Couleur changée !",
                description=f"Votre couleur de profil a été changée en **{color_name}**.",
                color=new_color
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Erreur de sauvegarde",
                description="Une erreur s'est produite lors de la sauvegarde.",
                color=BOT_CONFIG["error_color"]
            )
            await ctx.send(embed=embed)

    logger.info("All commands loaded successfully")
