import discord # type: ignore
from discord import app_commands
from discord.ext import commands
from discord.ext import commands, tasks # type: ignore
from collections import defaultdict
import requests #type:ignore
import gdown

intents = discord.Intents.all()
intents.messages = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

bad_words = ["chutiya", "lodu","fuck", "maderchod", "madarchod", "madarchoda", "madarchod", "madarchod",
    "bhenchod", "bhenchoda", "bhenchod", "bhenchod", "bsdk", "chutiya",
    "chutiye", "chutiye", "chutiya", "betichod", "betichoda", "betichod",
    "betichoda", "gandu", "chut", "lund"]  
user_levels = defaultdict(int)
user_xp = defaultdict(int)
spam_tracker = defaultdict(list)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await bot.tree.sync()
    level_up.start()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Check for bad words
    if any(word in message.content.lower() for word in bad_words):
        await message.delete()
        await message.channel.send(f"{message.author.mention}, please avoid using bad language!")
        return

    # Check for spam
    now = message.created_at.timestamp()
    spam_tracker[message.author.id].append(now)
    spam_tracker[message.author.id] = [t for t in spam_tracker[message.author.id] if now - t < 10]
    if len(spam_tracker[message.author.id]) > 5:
        await message.delete()
        await message.channel.send(f"{message.author.mention}, please do not spam!")
        return

    user_xp[message.author.id] += 3
    if user_xp[message.author.id] >= 1000:
        user_xp[message.author.id] = 0
        user_levels[message.author.id] += 1
        #await message.channel.send(f"Congratulations {message.author.mention}! You've leveled up to level {user_levels[message.author.id]}!")

    await bot.process_commands(message)

@tasks.loop(minutes=1)
async def level_up():
    for user_id in user_xp:
        user_xp[user_id] += 1

@bot.command()
async def mute(ctx, member: discord.Member, *, reason=None):
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not mute_role:
        mute_role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(mute_role, speak=False, send_messages=False)
    await member.add_roles(mute_role, reason=reason)
    await ctx.send(f"{member.mention} has been muted.")

@bot.command()
async def level(ctx, member: discord.Member = None):
    member = member or ctx.author
    level = user_levels[member.id]
    await ctx.send(f"{member.mention}, your level is {level}.")

@bot.command()
async def leaderboard(ctx):
    sorted_users = sorted(user_levels.items(), key=lambda x: x[1], reverse=True)
    leaderboard = "\n".join([f"<@{user_id}> - Level {level}" for user_id, level in sorted_users[:10]])
    await ctx.send(f"Leaderboard:\n{leaderboard}")

@bot.tree.command(name="ping",description= "Shows the bot's latency")
async def ping(interaction: discord.Interaction):
  await interaction.response.send_message(f"Hey {interaction.user.mention}! My latency is {round(bot.latency * 1000)}ms", ephemeral=True)

@bot.tree.command(name="say", description="Wanna say something??,Here is the chance!")
@app_commands.describe(thing_to_say = "synced")
async def say(interaction: discord.Interaction, thing_to_say: str, to: discord.Member): 
    await interaction.response.send_message(f"{interaction.user.mention} said: '{thing_to_say}' to {to.mention}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.content == "!meow":
        await message.channel.send("Meow! ")

    if message.content == "!catfact":
        try:
            response = requests.get("https://catfact.ninja/fact")
            cat_fact = response.json()["fact"]
            await message.channel.send(cat_fact)
        except Exception as e:
            print(f"Error fetching cat fact: {e}")
            await message.channel.send("Sorry, I could not fetch a fact at this time.")

    if message.content == "!nekopic":
        try:
            response = requests.get("https://api.thecatapi.com/v1/images/search")
            cat_image_url = response.json()[0]["url"]
            await message.channel.send(cat_image_url)
        except Exception as e:
            print(f"Error fetching cat image: {e}")
            await message.channel.send("Sorry, I could not fetch a cat image at this time.")

url = 'https://drive.google.com/u/0/uc?id=1F3ZGuaKN4ugYe_K1k9jLpAndTrNUvyWs'
output = 'token.txt'
gdown.download(url, output, quiet=False)

with open('token.txt') as f:
    TOKEN = f.readline()

bot.run(TOKEN)
