import discord
from beacon import BeaconBot

intents = discord.Intents.default()
bot = BeaconBot(command_prefix="?", intents=intents)


bot.run("YOUR_BOT_TOKEN_HERE")