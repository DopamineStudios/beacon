import discord
from beacon import Bot

intents = discord.Intents.default()
bot = Bot(command_prefix="?", intents=intents)


bot.run("YOUR_BOT_TOKEN_HERE")