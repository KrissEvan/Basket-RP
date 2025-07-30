import discord
from discord import app_commands
from discord.ext import commands
import logging
from datetime import datetime
from models import DatabaseManager
from config import BOT_CONFIG
from config import is_admin

logger = logging.getLogger(__name__)


def check_admin_permissions(interaction: discord.Interaction):
    """Vérifie si l'utilisateur a les permissions admin"""
    # Check if user is server owner (automatic admin access)
    if interaction.guild and interaction.guild.owner_id == interaction.user.id:
        return True

    # Check other admin permissions
    member = interaction.guild.get_member(
        interaction.user.id) if interaction.guild else None
    if member:
        user_roles = member.roles
        return is_admin(user_roles, member)

    return False


class AdminCommands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.db_manager = DatabaseManager()

    @app_commands.command(name="addpoints",
                          description="[ADMIN] Ajouter des points à un joueur")
    @app_commands.describe(joueur="Le joueur à qui ajouter des points",
                           points="Le nombre de points à ajouter")
    async def add_points(self, interaction: discord.Interaction,
                         joueur: discord.Member, points: int):
        """[ADMIN] Ajouter des points à un joueur"""
        if not check_admin_permissions(interaction):
            embed = discord.Embed(
                title="❌ Permission refusée",
                description=
                "Vous n'avez pas les permissions pour utiliser cette commande.",
                color=BOT_CONFIG["error_color"])
            await interaction.response.send_message(embed=embed,
                                                    ephemeral=True)
            return

        profile = self.db_manager.get_profile(joueur.id)
        if not profile:
            embed = discord.Embed(
                title="❌ Profil introuvable",
                description=f"{joueur.display_name} n'a pas de profil créé.",
                color=BOT_CONFIG["error_color"])
            await interaction.response.send_message(embed=embed,
                                                    ephemeral=True)
            return

        if points <= 0:
            embed = discord.Embed(
                title="❌ Points invalides",
                description="Vous devez ajouter au moins 1 point.",
                color=BOT_CONFIG["error_color"])
            await interaction.response.send_message(embed=embed,
                                                    ephemeral=True)
            return

        old_points = profile.available_points
        profile.available_points += points
        profile.updated_at = datetime.now()

        if self.db_manager.save_profile(profile):
            self.db_manager.log_action(joueur.id, "POINTS_ADDED",
                                       f"{points} points added by admin",
                                       interaction.user.id)
            embed = discord.Embed(
                title="✅ Points ajoutés !",
                description=
                f"**{joueur.display_name}** a reçu {points} points.\n\n**Points** : {old_points} → {profile.available_points} (+{points})",
                color=BOT_CONFIG["success_color"])
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Erreur de sauvegarde",
                description="Une erreur s'est produite lors de la sauvegarde.",
                color=BOT_CONFIG["error_color"])
            await interaction.response.send_message(embed=embed,
                                                    ephemeral=True)

    @app_commands.command(
        name="setstat",
        description="[ADMIN] Définir la valeur d'une statistique")
    @app_commands.describe(joueur="Le joueur à modifier",
                           statistique="La statistique à modifier",
                           valeur="La nouvelle valeur de la statistique")
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
    async def set_stat(self, interaction: discord.Interaction,
                       joueur: discord.Member, statistique: str, valeur: int):
        """[ADMIN] Définir une statistique"""
        if not check_admin_permissions(interaction):
            embed = discord.Embed(
                title="❌ Permission refusée",
                description=
                "Vous n'avez pas les permissions pour utiliser cette commande.",
                color=BOT_CONFIG["error_color"])
            await interaction.response.send_message(embed=embed,
                                                    ephemeral=True)
            return

        profile = self.db_manager.get_profile(joueur.id)
        if not profile:
            embed = discord.Embed(
                title="❌ Profil introuvable",
                description=f"{joueur.display_name} n'a pas de profil créé.",
                color=BOT_CONFIG["error_color"])
            await interaction.response.send_message(embed=embed,
                                                    ephemeral=True)
            return

        if valeur < 0 or valeur > BOT_CONFIG["max_stat_value"]:
            embed = discord.Embed(
                title="❌ Valeur invalide",
                description=
                f"La valeur doit être entre 0 et {BOT_CONFIG['max_stat_value']}.",
                color=BOT_CONFIG["error_color"])
            await interaction.response.send_message(embed=embed,
                                                    ephemeral=True)
            return

        old_value = profile.stats[statistique]
        profile.stats[statistique] = valeur
        profile.updated_at = datetime.now()

        if self.db_manager.save_profile(profile):
            self.db_manager.log_action(
                joueur.id, "STAT_CHANGED",
                f"{statistique}: {old_value} → {valeur}", interaction.user.id)
            embed = discord.Embed(
                title="✅ Statistique modifiée !",
                description=
                f"**{joueur.display_name}**\n\n**{statistique}** : {old_value} → {valeur}",
                color=BOT_CONFIG["success_color"])
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Erreur de sauvegarde",
                description="Une erreur s'est produite lors de la sauvegarde.",
                color=BOT_CONFIG["error_color"])
            await interaction.response.send_message(embed=embed,
                                                    ephemeral=True)

    @app_commands.command(
        name="setphysical",
        description="[ADMIN] Définir les caractéristiques physiques")
    @app_commands.describe(joueur="Le joueur à modifier",
                           taille="La taille en centimètres",
                           poids="Le poids en kilogrammes")
    async def set_physical(self,
                           interaction: discord.Interaction,
                           joueur: discord.Member,
                           taille: int = 0,
                           poids: int = 0):
        """[ADMIN] Définir la taille et le poids"""
        if not check_admin_permissions(interaction):
            embed = discord.Embed(
                title="❌ Permission refusée",
                description=
                "Vous n'avez pas les permissions pour utiliser cette commande.",
                color=BOT_CONFIG["error_color"])
            await interaction.response.send_message(embed=embed,
                                                    ephemeral=True)
            return

        profile = self.db_manager.get_profile(joueur.id)
        if not profile:
            embed = discord.Embed(
                title="❌ Profil introuvable",
                description=f"{joueur.display_name} n'a pas de profil créé.",
                color=BOT_CONFIG["error_color"])
            await interaction.response.send_message(embed=embed,
                                                    ephemeral=True)
            return

        if not taille and not poids:
            embed = discord.Embed(
                title="❌ Paramètres manquants",
                description=
                "Vous devez spécifier au moins la taille ou le poids.",
                color=BOT_CONFIG["error_color"])
            await interaction.response.send_message(embed=embed,
                                                    ephemeral=True)
            return

        changes = []
        if taille and taille > 0:
            profile.height = taille
            changes.append(f"**Taille** : {taille} cm")
        if poids and poids > 0:
            profile.weight = poids
            changes.append(f"**Poids** : {poids} kg")

        profile.updated_at = datetime.now()

        if self.db_manager.save_profile(profile):
            self.db_manager.log_action(joueur.id, "PHYSICAL_UPDATED",
                                       f"Height/Weight updated by admin",
                                       interaction.user.id)
            embed = discord.Embed(
                title="✅ Caractéristiques physiques modifiées !",
                description=f"**{joueur.display_name}**\n\n" +
                "\n".join(changes),
                color=BOT_CONFIG["success_color"])
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Erreur de sauvegarde",
                description="Une erreur s'est produite lors de la sauvegarde.",
                color=BOT_CONFIG["error_color"])
            await interaction.response.send_message(embed=embed,
                                                    ephemeral=True)

    @app_commands.command(
        name="deleteprofile",
        description="[ADMIN] Supprimer le profil d'un joueur")
    @app_commands.describe(joueur="Le joueur dont supprimer le profil")
    async def delete_profile(self, interaction: discord.Interaction,
                             joueur: discord.Member):
        """[ADMIN] Supprimer le profil d'un joueur"""
        if not check_admin_permissions(interaction):
            embed = discord.Embed(
                title="❌ Permission refusée",
                description=
                "Vous n'avez pas les permissions pour utiliser cette commande.",
                color=BOT_CONFIG["error_color"])
            await interaction.response.send_message(embed=embed,
                                                    ephemeral=True)
            return

        profile = self.db_manager.get_profile(joueur.id)
        if not profile:
            embed = discord.Embed(
                title="❌ Profil introuvable",
                description=f"{joueur.display_name} n'a pas de profil créé.",
                color=BOT_CONFIG["error_color"])
            await interaction.response.send_message(embed=embed,
                                                    ephemeral=True)
            return

        embed = discord.Embed(
            title="⚠️ Confirmation de suppression",
            description=
            f"Êtes-vous sûr de vouloir supprimer le profil de **{joueur.display_name}** ?\n\n**Cette action est irréversible !**",
            color=BOT_CONFIG["warning_color"])

        class ConfirmView(discord.ui.View):

            def __init__(self, db_manager, user_id):
                super().__init__(timeout=30)
                self.db_manager = db_manager
                self.user_id = user_id

            @discord.ui.button(label="Confirmer",
                               style=discord.ButtonStyle.danger,
                               emoji="🗑️")
            async def confirm(self, interaction_btn: discord.Interaction,
                              button: discord.ui.Button):
                if self.db_manager.delete_profile(joueur.id):
                    self.db_manager.log_action(joueur.id, "PROFILE_DELETED",
                                               f"Profile deleted by admin",
                                               self.user_id)
                    embed = discord.Embed(
                        title="✅ Profil supprimé !",
                        description=
                        f"Le profil de **{joueur.display_name}** a été supprimé avec succès.",
                        color=BOT_CONFIG["success_color"])
                else:
                    embed = discord.Embed(
                        title="❌ Erreur de suppression",
                        description=
                        "Une erreur s'est produite lors de la suppression.",
                        color=BOT_CONFIG["error_color"])
                await interaction_btn.response.edit_message(embed=embed,
                                                            view=None)

            @discord.ui.button(label="Annuler",
                               style=discord.ButtonStyle.secondary,
                               emoji="❌")
            async def cancel(self, interaction_btn: discord.Interaction,
                             button: discord.ui.Button):
                embed = discord.Embed(
                    title="❌ Suppression annulée",
                    description="Le profil n'a pas été supprimé.",
                    color=BOT_CONFIG["embed_color"])
                await interaction_btn.response.edit_message(embed=embed,
                                                            view=None)

        await interaction.response.send_message(embed=embed,
                                                view=ConfirmView(
                                                    self.db_manager,
                                                    interaction.user.id),
                                                ephemeral=True)

    @app_commands.command(
        name="resetplayer",
        description="[ADMIN] Réinitialiser complètement un joueur")
    @app_commands.describe(joueur="Le joueur à réinitialiser")
    async def reset_player(self, interaction: discord.Interaction,
                           joueur: discord.Member):
        """[ADMIN] Réinitialiser un joueur"""
        if not check_admin_permissions(interaction):
            embed = discord.Embed(
                title="❌ Permission refusée",
                description=
                "Vous n'avez pas les permissions pour utiliser cette commande.",
                color=BOT_CONFIG["error_color"])
            await interaction.response.send_message(embed=embed,
                                                    ephemeral=True)
            return

        profile = self.db_manager.get_profile(joueur.id)
        if not profile:
            embed = discord.Embed(
                title="❌ Profil introuvable",
                description=f"{joueur.display_name} n'a pas de profil créé.",
                color=BOT_CONFIG["error_color"])
            await interaction.response.send_message(embed=embed,
                                                    ephemeral=True)
            return

        embed = discord.Embed(
            title="⚠️ Confirmation de réinitialisation",
            description=
            f"Êtes-vous sûr de vouloir réinitialiser complètement **{joueur.display_name}** ?\n\n**Cela va :**\n• Remettre toutes les stats à 50\n• Remettre les points disponibles à 0\n• Garder l'archétype et les informations personnelles\n\n**Cette action est irréversible !**",
            color=BOT_CONFIG["warning_color"])

        class ResetConfirmView(discord.ui.View):

            def __init__(self, db_manager, user_id):
                super().__init__(timeout=30)
                self.db_manager = db_manager
                self.user_id = user_id

            @discord.ui.button(label="Confirmer",
                               style=discord.ButtonStyle.danger,
                               emoji="🔄")
            async def confirm(self, interaction_btn: discord.Interaction,
                              button: discord.ui.Button):
                # Reset all stats to base value
                base_stats = BOT_CONFIG["base_stats"].copy()
                archetype_bonuses = BOT_CONFIG["archetype_bonuses"].get(
                    profile.archetype, {})

                for stat in base_stats:
                    base_stats[stat] += archetype_bonuses.get(stat, 0)

                profile.stats = base_stats
                profile.available_points = 0
                profile.updated_at = datetime.now()

                if self.db_manager.save_profile(profile):
                    self.db_manager.log_action(joueur.id, "PLAYER_RESET",
                                               f"Player stats reset by admin",
                                               self.user_id)
                    embed = discord.Embed(
                        title="✅ Joueur réinitialisé !",
                        description=
                        f"**{joueur.display_name}** a été réinitialisé avec succès.\n\nTous les stats sont revenus aux valeurs de base + bonus d'archétype.",
                        color=BOT_CONFIG["success_color"])
                else:
                    embed = discord.Embed(
                        title="❌ Erreur de réinitialisation",
                        description=
                        "Une erreur s'est produite lors de la réinitialisation.",
                        color=BOT_CONFIG["error_color"])
                await interaction_btn.response.edit_message(embed=embed,
                                                            view=None)

            @discord.ui.button(label="Annuler",
                               style=discord.ButtonStyle.secondary,
                               emoji="❌")
            async def cancel(self, interaction_btn: discord.Interaction,
                             button: discord.ui.Button):
                embed = discord.Embed(
                    title="❌ Réinitialisation annulée",
                    description="Le joueur n'a pas été réinitialisé.",
                    color=BOT_CONFIG["embed_color"])
                await interaction_btn.response.edit_message(embed=embed,
                                                            view=None)

        await interaction.response.send_message(embed=embed,
                                                view=ResetConfirmView(
                                                    self.db_manager,
                                                    interaction.user.id),
                                                ephemeral=True)


async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
