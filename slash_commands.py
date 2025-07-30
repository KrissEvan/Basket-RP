import discord
from discord import app_commands
from discord.ext import commands
import logging
from datetime import datetime
from models import PlayerProfile, DatabaseManager
from config import BOT_CONFIG, ARCHETYPES, STAT_EMOJIS, COLOR_MAPPING, get_archetype_from_roles, is_admin, get_color_from_name

# Define stat names and emojis
STAT_NAMES = ["Force Physique", "Précision", "Manip. Ballon", "Agilité", "Détente", "Défense", "Vitesse", "Endurance"]

def get_stat_emoji(stat_name):
    return STAT_EMOJIS.get(stat_name, "📊")

logger = logging.getLogger(__name__)

class BasketballCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_manager = DatabaseManager()

    @app_commands.command(name="create", description="Créer votre profil de joueur de basketball")
    async def create_profile(self, interaction: discord.Interaction):
        """Créer un profil de joueur"""
        try:
            # Vérifier si le profil existe déjà
            existing_profile = self.db_manager.get_profile(interaction.user.id)
            if existing_profile:
                embed = discord.Embed(
                    title="❌ Profil existant",
                    description="Vous avez déjà un profil créé ! Utilisez `/profile` pour le voir.",
                    color=BOT_CONFIG["error_color"]
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Détecter l'archétype basé sur les rôles
            # Note: Les membres dans les interactions slash n'ont pas toujours l'accès aux rôles
            # Nous devons récupérer le membre depuis le guild
            if interaction.guild:
                member = interaction.guild.get_member(interaction.user.id)
                if member:
                    archetype = get_archetype_from_roles(member.roles)
                else:
                    archetype = None
            else:
                archetype = None
            
            if not archetype:
                available_roles = ", ".join(ARCHETYPES.keys())
                embed = discord.Embed(
                    title="❌ Aucun rôle de position détecté",
                    description=f"Vous devez avoir un des rôles suivants pour créer un profil :\n{available_roles}",
                    color=BOT_CONFIG["error_color"]
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # Créer le profil
            profile = PlayerProfile(
                user_id=interaction.user.id,
                username=interaction.user.display_name,
                archetype=archetype
            )

            # Sauvegarder le profil
            if self.db_manager.save_profile(profile):
                self.db_manager.log_action(interaction.user.id, "PROFILE_CREATED", f"Archetype: {archetype}")
                
                archetype_info = ARCHETYPES[archetype]
                embed = discord.Embed(
                    title="✅ Profil créé avec succès !",
                    description=f"**{interaction.user.display_name}** - {archetype}",
                    color=BOT_CONFIG["success_color"]
                )
                
                embed.add_field(
                    name=f"🏀 {archetype}",
                    value=archetype_info["description"],
                    inline=False
                )

                # Afficher les bonus d'archétype
                bonuses = []
                for stat, bonus in archetype_info["bonuses"].items():
                    if bonus > 0:
                        emoji = get_stat_emoji(stat)
                        bonuses.append(f"{emoji} {stat}: +{bonus}")
                
                if bonuses:
                    embed.add_field(
                        name="📈 Bonus d'archétype",
                        value="\n".join(bonuses),
                        inline=False
                    )

                # Afficher les stats initiales
                stats_text = ""
                for stat_name in STAT_NAMES:
                    emoji = get_stat_emoji(stat_name)
                    value = profile.stats[stat_name]
                    stats_text += f"{emoji} **{stat_name}**: {value}/1000\n"
                
                embed.add_field(
                    name="📊 Statistiques initiales",
                    value=stats_text,
                    inline=True
                )
                
                embed.add_field(
                    name="💎 Points disponibles",
                    value=f"{profile.available_points}",
                    inline=True
                )
                
                embed.add_field(
                    name="🎯 Total des stats",
                    value=f"{profile.get_total_stats()}/8000",
                    inline=True
                )

                embed.set_footer(text="Utilisez /addstat pour améliorer vos statistiques")
                await interaction.response.send_message(embed=embed)
            else:
                embed = discord.Embed(
                    title="❌ Erreur de création",
                    description="Une erreur s'est produite lors de la création de votre profil.",
                    color=BOT_CONFIG["error_color"]
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Erreur lors de la création du profil: {e}")
            embed = discord.Embed(
                title="❌ Erreur interne",
                description="Une erreur inattendue s'est produite.",
                color=BOT_CONFIG["error_color"]
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="profile", description="Voir votre profil ou celui d'un autre joueur")
    @app_commands.describe(joueur="Le joueur dont vous voulez voir le profil")
    async def show_profile(self, interaction: discord.Interaction, joueur: discord.Member = None):
        """Afficher un profil de joueur"""
        target_user = joueur if joueur else interaction.user
        
        profile = self.db_manager.get_profile(target_user.id)
        if not profile:
            if target_user == interaction.user:
                embed = discord.Embed(
                    title="❌ Profil introuvable",
                    description="Vous n'avez pas encore créé de profil. Utilisez `/create`.",
                    color=BOT_CONFIG["error_color"]
                )
            else:
                embed = discord.Embed(
                    title="❌ Profil introuvable",
                    description=f"{target_user.display_name} n'a pas de profil créé.",
                    color=BOT_CONFIG["error_color"]
                )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Créer l'embed du profil
        embed_color = profile.embed_color if hasattr(profile, 'embed_color') and profile.embed_color else BOT_CONFIG["embed_color"]
        
        # Titre avec informations personnalisées
        title_parts = []
        if hasattr(profile, 'character_name') and profile.character_name:
            title_parts.append(profile.character_name)
        if hasattr(profile, 'first_name') and profile.first_name:
            title_parts.append(f"({profile.first_name})")
        
        if title_parts:
            profile_title = " ".join(title_parts)
        else:
            profile_title = profile.username
            
        embed = discord.Embed(
            title=f"🏀 {profile_title}",
            description=f"**Archétype**: {profile.archetype}",
            color=embed_color
        )

        # Informations personnalisées
        personal_info = []
        if hasattr(profile, 'age') and profile.age:
            personal_info.append(f"**Âge**: {profile.age} ans")
        if hasattr(profile, 'height') and profile.height:
            personal_info.append(f"**Taille**: {profile.height} cm")
        if hasattr(profile, 'weight') and profile.weight:
            personal_info.append(f"**Poids**: {profile.weight} kg")
        
        if personal_info:
            embed.add_field(
                name="👤 Informations personnelles",
                value="\n".join(personal_info),
                inline=True
            )

        # Statistiques
        stats_text = ""
        for stat_name in STAT_NAMES:
            emoji = get_stat_emoji(stat_name)
            value = profile.stats[stat_name]
            stats_text += f"{emoji} **{stat_name}**: {value}/1000\n"
        
        embed.add_field(
            name="📊 Statistiques",
            value=stats_text,
            inline=True
        )
        
        # Informations sur l'archétype
        if profile.archetype in ARCHETYPES:
            archetype_info = ARCHETYPES[profile.archetype]
            embed.add_field(
                name=f"🏀 {profile.archetype}",
                value=archetype_info["description"],
                inline=False
            )
        
        # Points et total
        embed.add_field(name="💎 Points disponibles", value=f"{profile.available_points}", inline=True)
        total_stats = profile.get_total_stats()
        embed.add_field(name="🎯 Total des stats", value=f"{total_stats}/8000", inline=True)
        
        # Image de profil si disponible
        if hasattr(profile, 'profile_image') and profile.profile_image:
            embed.set_thumbnail(url=profile.profile_image)
        
        # Footer avec date de création
        embed.set_footer(text=f"Profil créé le {profile.created_at.strftime('%d/%m/%Y')}")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="addstat", description="Ajouter des points à une statistique")
    @app_commands.describe(
        statistique="La statistique à améliorer",
        points="Le nombre de points à ajouter"
    )
    @app_commands.choices(statistique=[
        app_commands.Choice(name="Force Physique", value="Force Physique"),
        app_commands.Choice(name="Précision", value="Précision"),
        app_commands.Choice(name="Manip. Ballon", value="Manip. Ballon"),
        app_commands.Choice(name="Agilité", value="Agilité"),
        app_commands.Choice(name="Détente", value="Détente"),
        app_commands.Choice(name="Défense", value="Défense"),
        app_commands.Choice(name="Vitesse", value="Vitesse"),
        app_commands.Choice(name="Endurance", value="Endurance")
    ])
    async def add_stat(self, interaction: discord.Interaction, statistique: str, points: int):
        """Ajouter des points à une statistique"""
        profile = self.db_manager.get_profile(interaction.user.id)
        if not profile:
            embed = discord.Embed(
                title="❌ Profil introuvable",
                description="Vous devez créer un profil avant d'ajouter des stats. Utilisez `/create`.",
                color=BOT_CONFIG["error_color"]
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Validation des points
        if points <= 0:
            embed = discord.Embed(
                title="❌ Points invalides",
                description="Vous devez ajouter au moins 1 point.",
                color=BOT_CONFIG["error_color"]
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if points > profile.available_points:
            embed = discord.Embed(
                title="❌ Points insuffisants",
                description=f"Vous n'avez que {profile.available_points} points disponibles.",
                color=BOT_CONFIG["error_color"]
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        current_stat = profile.stats[statistique]
        if current_stat + points > BOT_CONFIG["max_stat_value"]:
            max_addable = BOT_CONFIG["max_stat_value"] - current_stat
            embed = discord.Embed(
                title="❌ Limite de stat atteinte",
                description=f"Vous ne pouvez ajouter que {max_addable} points maximum à {statistique} (actuellement {current_stat}/1000).",
                color=BOT_CONFIG["error_color"]
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Ajouter les points
        profile.stats[statistique] += points
        profile.available_points -= points
        profile.updated_at = datetime.now()

        if self.db_manager.save_profile(profile):
            self.db_manager.log_action(interaction.user.id, "STAT_ADDED", f"{statistique}: +{points}")
            
            emoji = get_stat_emoji(statistique)
            embed = discord.Embed(
                title="✅ Statistique améliorée !",
                description=f"{emoji} **{statistique}** : {current_stat} → {profile.stats[statistique]} (+{points})",
                color=BOT_CONFIG["success_color"]
            )
            embed.add_field(
                name="💎 Points restants",
                value=f"{profile.available_points}",
                inline=True
            )
            embed.add_field(
                name="🎯 Total des stats",
                value=f"{profile.get_total_stats()}/8000",
                inline=True
            )
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Erreur de sauvegarde",
                description="Une erreur s'est produite lors de la sauvegarde.",
                color=BOT_CONFIG["error_color"]
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="customize", description="Personnaliser votre profil")
    @app_commands.describe(
        champ="Le champ à modifier",
        valeur="La nouvelle valeur"
    )
    @app_commands.choices(champ=[
        app_commands.Choice(name="Nom", value="nom"),
        app_commands.Choice(name="Prénom", value="prénom"),
        app_commands.Choice(name="Âge", value="âge"),
        app_commands.Choice(name="Image", value="image")
    ])
    async def customize_profile(self, interaction: discord.Interaction, champ: str, valeur: str):
        """Personnaliser son profil"""
        profile = self.db_manager.get_profile(interaction.user.id)
        if not profile:
            embed = discord.Embed(
                title="❌ Profil introuvable",
                description="Vous devez créer un profil avant de le personnaliser. Utilisez `/create`.",
                color=BOT_CONFIG["error_color"]
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if champ == "nom":
            profile.character_name = valeur
            field_name = "nom"
        elif champ == "prénom":
            profile.first_name = valeur
            field_name = "prénom"
        elif champ == "âge":
            try:
                profile.age = int(valeur)
                field_name = "âge"
            except ValueError:
                embed = discord.Embed(
                    title="❌ Âge invalide",
                    description="L'âge doit être un nombre entier.",
                    color=BOT_CONFIG["error_color"]
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        elif champ == "image":
            profile.profile_image = valeur
            field_name = "image"
        else:
            field_name = "champ"

        profile.updated_at = datetime.now()
        if self.db_manager.save_profile(profile):
            self.db_manager.log_action(interaction.user.id, "PROFILE_CUSTOMIZED", f"{field_name} updated")
            embed = discord.Embed(
                title="✅ Profil mis à jour !",
                description=f"Votre {field_name} a été mis à jour avec succès.",
                color=BOT_CONFIG["success_color"]
            )
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Erreur de sauvegarde",
                description="Une erreur s'est produite lors de la sauvegarde.",
                color=BOT_CONFIG["error_color"]
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="color", description="Changer la couleur de votre profil")
    @app_commands.describe(couleur="La couleur à utiliser pour votre profil")
    @app_commands.choices(couleur=[
        app_commands.Choice(name="Rouge", value="rouge"),
        app_commands.Choice(name="Bleu", value="bleu"),
        app_commands.Choice(name="Vert", value="vert"),
        app_commands.Choice(name="Orange", value="orange"),
        app_commands.Choice(name="Violet", value="violet"),
        app_commands.Choice(name="Rose", value="rose"),
        app_commands.Choice(name="Jaune", value="jaune"),
        app_commands.Choice(name="Cyan", value="cyan"),
        app_commands.Choice(name="Gris", value="gris"),
        app_commands.Choice(name="Noir", value="noir")
    ])
    async def set_color(self, interaction: discord.Interaction, couleur: str):
        """Changer la couleur de son profil"""
        profile = self.db_manager.get_profile(interaction.user.id)
        if not profile:
            embed = discord.Embed(
                title="❌ Profil introuvable",
                description="Vous devez créer un profil avant de changer la couleur. Utilisez `/create`.",
                color=BOT_CONFIG["error_color"]
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        new_color = get_color_from_name(couleur)
        profile.embed_color = new_color
        profile.updated_at = datetime.now()
        
        if self.db_manager.save_profile(profile):
            self.db_manager.log_action(interaction.user.id, "COLOR_CHANGED", f"Color changed to {couleur}")
            embed = discord.Embed(
                title="✅ Couleur changée !",
                description=f"Votre couleur de profil a été changée en **{couleur}**.",
                color=new_color
            )
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Erreur de sauvegarde",
                description="Une erreur s'est produite lors de la sauvegarde.",
                color=BOT_CONFIG["error_color"]
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="leaderboard", description="Voir le classement des joueurs")
    @app_commands.describe(statistique="La statistique pour le classement (optionnel)")
    @app_commands.choices(statistique=[
        app_commands.Choice(name="Force Physique", value="Force Physique"),
        app_commands.Choice(name="Précision", value="Précision"),
        app_commands.Choice(name="Manip. Ballon", value="Manip. Ballon"),
        app_commands.Choice(name="Agilité", value="Agilité"),
        app_commands.Choice(name="Détente", value="Détente"),
        app_commands.Choice(name="Défense", value="Défense"),
        app_commands.Choice(name="Vitesse", value="Vitesse"),
        app_commands.Choice(name="Endurance", value="Endurance")
    ])
    async def leaderboard(self, interaction: discord.Interaction, statistique: str = None):
        """Afficher le classement"""
        profiles = self.db_manager.get_all_profiles()
        if not profiles:
            embed = discord.Embed(
                title="❌ Aucun profil",
                description="Aucun joueur n'a encore créé de profil.",
                color=BOT_CONFIG["error_color"]
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if statistique:
            # Classement par statistique spécifique
            profiles.sort(key=lambda p: p.stats[statistique], reverse=True)
            emoji = STAT_EMOJIS.get(statistique, "📊")
            
            embed = discord.Embed(
                title=f"🏆 Classement - {emoji} {statistique}",
                color=BOT_CONFIG["embed_color"]
            )
            
            leaderboard_text = ""
            for i, profile in enumerate(profiles[:10], 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                stat_value = profile.stats[statistique]
                leaderboard_text += f"{medal} **{profile.username}** - {stat_value}/1000\n"
            
            embed.description = leaderboard_text
            
        else:
            # Classement général (total des stats)
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
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="help", description="Afficher la liste des commandes disponibles")
    async def help_command(self, interaction: discord.Interaction):
        """Afficher l'aide"""
        embed = discord.Embed(
            title="🏀 Commandes Basketball Bot",
            description="Voici toutes les commandes disponibles :",
            color=BOT_CONFIG["embed_color"]
        )
        
        # Commandes principales
        embed.add_field(
            name="📋 Commandes principales",
            value=(
                "`/create` - Créer votre profil de joueur\n"
                "`/profile [joueur]` - Voir un profil\n"
                "`/addstat <stat> <points>` - Améliorer une statistique\n"
                "`/leaderboard [stat]` - Voir le classement\n"
            ),
            inline=False
        )
        
        # Personnalisation
        embed.add_field(
            name="🎨 Personnalisation",
            value=(
                "`/customize <champ> <valeur>` - Personnaliser profil\n"
                "`/color <couleur>` - Changer couleur profil\n"
            ),
            inline=False
        )
        
        # Commandes admin
        embed.add_field(
            name="⚙️ Commandes Admin",
            value=(
                "`/addpoints <joueur> <points>` - Ajouter points\n"
                "`/setstat <joueur> <stat> <valeur>` - Modifier stat\n"
                "`/setphysical <joueur> [taille] [poids]` - Définir physique\n"
                "`/deleteprofile <joueur>` - Supprimer profil\n"
                "`/resetplayer <joueur>` - Réinitialiser joueur\n"
            ),
            inline=False
        )
        
        # Informations supplémentaires
        embed.add_field(
            name="📊 Statistiques",
            value="Force Physique, Précision, Manip. Ballon, Agilité, Détente, Défense, Vitesse, Endurance",
            inline=False
        )
        
        embed.add_field(
            name="🏀 Archétypes",
            value="Meneur, Arrière, Ailier, Ailier Fort, Pivot",
            inline=False
        )
        
        embed.set_footer(text="Toutes les commandes utilisent maintenant le système de commandes slash (/)")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="debug", description="Diagnostiquer les permissions et informations utilisateur")
    async def debug_command(self, interaction: discord.Interaction):
        """Commande de diagnostic pour les permissions"""
        logger.info(f"=== DEBUG COMMAND ===")
        logger.info(f"User ID: {interaction.user.id}")
        logger.info(f"User: {interaction.user.name}")
        logger.info(f"Guild: {interaction.guild.name if interaction.guild else 'None'}")
        logger.info(f"Guild Owner ID: {interaction.guild.owner_id if interaction.guild else 'None'}")
        
        is_owner = interaction.guild and interaction.guild.owner_id == interaction.user.id
        logger.info(f"Is Owner: {is_owner}")
        
        member = interaction.guild.get_member(interaction.user.id) if interaction.guild else None
        
        embed = discord.Embed(
            title="🔍 Diagnostic des Permissions",
            color=BOT_CONFIG["embed_color"]
        )
        
        embed.add_field(
            name="Informations Utilisateur",
            value=f"**ID:** {interaction.user.id}\n**Nom:** {interaction.user.display_name}\n**Propriétaire du serveur:** {'✅ Oui' if is_owner else '❌ Non'}",
            inline=False
        )
        
        if member:
            logger.info(f"Member found: {member.display_name}")
            logger.info(f"Administrator: {member.guild_permissions.administrator}")
            logger.info(f"Manage Guild: {member.guild_permissions.manage_guild}")
            
            embed.add_field(
                name="Permissions Discord",
                value=f"**Administrateur:** {'✅' if member.guild_permissions.administrator else '❌'}\n**Gérer le serveur:** {'✅' if member.guild_permissions.manage_guild else '❌'}",
                inline=False
            )
            
            roles_list = [role.name for role in member.roles[1:]]  # Skip @everyone
            embed.add_field(
                name="Rôles",
                value=", ".join(roles_list) if roles_list else "Aucun rôle spécifique",
                inline=False
            )
        else:
            logger.info("Member not found!")
            embed.add_field(
                name="Erreur",
                value="❌ Impossible de récupérer les informations du membre",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(BasketballCommands(bot))