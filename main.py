import os
import asyncio
import logging
import discord
from discord.ext import commands
from discord import app_commands
from database import init_db
from commands import setup_commands

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    """Event triggered when the bot is ready"""
    logger.info(f'{bot.user} has connected to Discord!')
    logger.info(f'Bot is in {len(bot.guilds)} guilds')
    
    # Initialize database
    await init_db()
    logger.info('Database initialized successfully')
    
    # Setup commands
    await setup_commands(bot)
    logger.info('Commands loaded successfully')
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        logger.info(f'Synced {len(synced)} slash commands')
    except Exception as e:
        logger.error(f'Failed to sync slash commands: {e}')

@bot.event
async def on_member_join(member):
    """Event triggered when a new member joins"""
    logger.info(f'New member joined: {member.name} ({member.id})')

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for commands"""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Commande inconnue. Utilisez `!help` pour voir les commandes disponibles.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Argument manquant. Utilisez `!help {ctx.command}` pour plus d'informations.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Argument invalide. Vérifiez le format de votre commande.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Vous n'avez pas les permissions nécessaires pour cette commande.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("❌ Le bot n'a pas les permissions nécessaires.")
    else:
        logger.error(f'Unhandled error in command {ctx.command}: {error}', exc_info=True)
        await ctx.send("❌ Une erreur inattendue s'est produite. Contactez un administrateur.")

async def main():
    """Main function to start the bot"""
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        logger.error('DISCORD_TOKEN environment variable not found!')
        return
    
    try:
        await bot.start(token)
    except discord.LoginFailure:
        logger.error('Invalid Discord token provided!')
    except Exception as e:
        logger.error(f'Failed to start bot: {e}', exc_info=True)

if __name__ == '__main__':
    asyncio.run(main())
