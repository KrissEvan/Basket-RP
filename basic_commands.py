import discord
from discord import app_commands
from discord.ext import commands

class Basic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Répond avec Pong !")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("🏓 Pong !")

    @app_commands.command(name="hello", description="Dit bonjour à l'utilisateur")
    async def hello(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"👋 Salut {interaction.user.mention} !")

async def setup(bot):
    await bot.add_cog(Basic(bot))
