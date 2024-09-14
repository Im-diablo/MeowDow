""" ===============================================  PACKAGES  ================================================================= """
import aiohttp
import asyncio
import datetime
import discord
import gdown
import json
import logging
import math
import psutil
import platform
import random
import re
import requests
import spotipy
import time
import yt_dlp

from better_profanity import profanity
from async_timeout import timeout
from collections import defaultdict
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import has_permissions
from discord.ui import Button, View
from spotipy.oauth2 import SpotifyClientCredentials
from youtubesearchpython import VideosSearch

""" ===============================================  TOKEN FOR BOT ================================================================= """

url = 'https://drive.google.com/u/0/uc?id=1-IlWaujV4qkIJPxrOitYiV7f3T8-bMWU'
output = 'token.txt'
gdown.download(url, output, quiet=False)
with open('token.txt') as f:
    TOKEN = f.readline()

""" ===============================================  API FOR GIF  ================================================================= """

url = 'https://drive.google.com/u/0/uc?id=1nnkdj-GlrYh-QuHRkJxOm0bm56mu7zgJ'
output = 'giphy.txt'
gdown.download(url, output, quiet=False)
with open('giphy.txt') as f:
    GIPHY_API_KEY = f.readline()


""" ===============================================  SPOTIFY  ================================================================= """

''' CLIENT_ID '''
url = 'https://drive.google.com/u/0/uc?id=1wqfzSiZtvlO5x2Q-BrdxkAaamJlKzQD-'
output = 'spotify_id.txt'
gdown.download(url, output, quiet=False)
with open('spotify_id.txt') as f:
    SPOTIFY_CLIENT_ID = f.readline()

''' CLIENT_SECRET '''
url = 'https://drive.google.com/u/0/uc?id=16bwYLuxHqFF4sKwkI5-N7MrL8pZE4rb0'
output = 'spotify_sec.txt'
gdown.download(url, output, quiet=False)
with open('spotify_sec.txt') as f:
    SPOTIFY_CLIENT_SECRET = f.readline()

    
""" ============================================ INTENTS AND PREFIX  ========================================================== """

intents = discord.Intents.all()
intents.messages = True
intents.guilds = True
intents.members = True
intents.voice_states = True

Bot = commands.Bot(command_prefix=".", intents=intents)


""" ============================================  BOT SYNC COMMAND  ============================================================= """

@Bot.command()
@commands.is_owner()
async def sync(ctx):
    synced = await Bot.tree.sync()
    await ctx.send(f"Synced {len(synced)} commands.")

""" =============================================== ON READY ================================================================  """

@Bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {Bot.user}')
    await Bot.tree.sync()
    print('Command tree synced')
    #await Bot.change_presence(activity=discord.Game(name="Hanging out in Harmony"))
    await Bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="HER"))
    #await Bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="over YOU"))
    #await Bot.change_presence(activity=discord.Streaming(name="my development", url="https://www.twitch.tv/yourchannelhere"))


''' =============================================== PING ================================================================='''

@Bot.command(help="Answers with pong and bot's latency",
             description="(prefix)ping to get the bot's latency",
             brief="Answers with pong and bot's latency")
async def ping(ctx):
    # Initial embed
    embed = discord.Embed(title="Pong!", description="Calculating ping...", color=discord.Color.yellow())
    message = await ctx.send(embed=embed)
    
    # Animated ping calculation
    for i in range(3):
        latency = round(Bot.latency * 1000)
        embed.description = f"Calculating ping{'.' * (i + 1)}"
        await message.edit(embed=embed)
        await asyncio.sleep(0.5)
    
    # Final embed
    latency = round(Bot.latency * 1000)
    embed.title = "Pong! 🏓"
    embed.description = None
    embed.color = discord.Color.yellow()
    embed.add_field(name="Latency", value=f"{latency}ms", inline=False)
    embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
    
    await message.edit(embed=embed)


""" ===============================================  BAD WORDS  ================================================================= """

def get_bad_words(url):
    response = requests.get(url)
    if response.status_code == 200:
        words = response.text.split('\n')
        return set(word.strip().lower() for word in words if word.strip())
    else:
        print(f"Failed to fetch words list from {url}. Using a default list.")
        return set()  # Return an empty set if fetch fails

# URLs for bad words lists
MAIN_BAD_WORDS_URL = "https://raw.githubusercontent.com/RobertJGabriel/Google-profanity-words/master/list.txt"
CUSTOM_BAD_WORDS_URL = "https://raw.githubusercontent.com/phantom-exe/stock/main/custom_bad_words.txt"

# Fetch both lists
MAIN_BAD_WORDS = get_bad_words(MAIN_BAD_WORDS_URL)
CUSTOM_BAD_WORDS = get_bad_words(CUSTOM_BAD_WORDS_URL)

# Combine both sets
BAD_WORDS = MAIN_BAD_WORDS.union(CUSTOM_BAD_WORDS)
profanity.load_censor_words(BAD_WORDS)

# Variable to store the state of the bad words filter
bad_words_filter_enabled = True

def contains_bad_word(message):
    return profanity.contains_profanity(message)

@Bot.tree.command(name="toggle_filter", description="Toggle the bad words filter on/off")
@commands.has_permissions(administrator=True)
async def toggle_filter(interaction: discord.Interaction):
    global bad_words_filter_enabled
    bad_words_filter_enabled = not bad_words_filter_enabled
    status = "enabled" if bad_words_filter_enabled else "disabled"
    await interaction.response.send_message(f"Bad words filter has been {status}.", ephemeral=True)

@Bot.event
async def on_message(message):
    if message.author == Bot.user:
        return

    if bad_words_filter_enabled and contains_bad_word(message.content):
        await message.delete()
        await message.channel.send(f"{message.author.mention}, please watch your language!")
        return

    await Bot.process_commands(message)



""" ===========================================  SPAM DETECTION  ============================================================== """


class SpamDetector:
    def __init__(self):
        self.message_count = defaultdict(int)
        self.last_reset = defaultdict(float)
        self.muted_users = set()
        self.user_messages = defaultdict(list)
        self.THRESHOLD = 5
        self.TIME_WINDOW = 5  # seconds
        self.TIMEOUT_DURATION = 60  # seconds

    async def check_spam(self, message):
        user_id = message.author.id
        current_time = time.time()

        if current_time - self.last_reset[user_id] > self.TIME_WINDOW:
            self.message_count[user_id] = 0
            self.last_reset[user_id] = current_time
            self.user_messages[user_id] = []

        self.message_count[user_id] += 1
        self.user_messages[user_id].append(message)

        if self.message_count[user_id] > self.THRESHOLD:
            if user_id not in self.muted_users:
                await self.timeout_user(message)
            return True
        return False

    async def timeout_user(self, message):
        user_id = message.author.id
        self.muted_users.add(user_id)
        
        try:
            # Delete spammed messages
            for msg in self.user_messages[user_id]:
                try:
                    await msg.delete()
                except discord.errors.NotFound:
                    pass  # Message already deleted

            # Timeout the user
            await message.author.timeout(discord.utils.utcnow() + datetime.timedelta(seconds=self.TIMEOUT_DURATION), reason="Spamming")
            await message.channel.send(f"{message.author.mention} has been timed out for {self.TIMEOUT_DURATION} seconds due to spamming.")

            # Wait for the timeout duration
            await asyncio.sleep(self.TIMEOUT_DURATION)

            # Remove the timeout
            await message.author.timeout(None, reason="Timeout duration expired")
            self.muted_users.remove(user_id)
            await message.channel.send(f"{message.author.mention}'s timeout has been lifted.")
        except discord.errors.Forbidden:
            await message.channel.send("I don't have permission to timeout users or delete messages.")

spam_detector = SpamDetector()

@Bot.event
async def on_message(message):
    print(f"Message received: {message.content}")  # Debug print
    if message.author == Bot.user:
        return

    if bad_words_filter_enabled:
        print(f"Checking message: {message.content}")  # Debug print
        if contains_bad_word(message.content):
            print("Bad word detected!")  # Debug print
            await message.delete()
            await message.channel.send(f"{message.author.mention}, please watch your language!")
            return

    await Bot.process_commands(message)

        
"""============================================  MUTE AND UNMUTE ============================================================="""

@Bot.event
async def on_guild_channel_create(channel):
    muted_role = discord.utils.get(channel.guild.roles, name="Muted")
    if muted_role:
        await channel.set_permissions(muted_role, speak=False, send_messages=False, add_reactions=False)
@Bot.tree.command(name="mute", description="Mute a member in the server")
@app_commands.describe(member="The member to mute", reason="Reason for muting")
@app_commands.checks.has_permissions(manage_roles=True)
async def mute(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    # Check if the bot has the necessary permissions
    if not interaction.guild.me.guild_permissions.manage_roles:
        await interaction.response.send_message("I don't have the necessary permissions to manage roles.", ephemeral=True)
        return

    # Check if the member is already muted
    muted_role = discord.utils.get(interaction.guild.roles, name="Muted")
    if muted_role in member.roles:
        await interaction.response.send_message(f"{member.mention} is already muted.", ephemeral=True)
        return

    # Create the Muted role if it doesn't exist
    if not muted_role:
        try:
            muted_role = await interaction.guild.create_role(name="Muted", reason="To use for muting")
            for channel in interaction.guild.channels:
                await channel.set_permissions(muted_role, send_messages=False, add_reactions=False)
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to create roles.", ephemeral=True)
            return

    # Attempt to add the Muted role to the member
    try:
        await member.add_roles(muted_role, reason=reason)
        await interaction.response.send_message(f'{member.mention} has been muted. Reason: {reason}')
    except discord.Forbidden:
        await interaction.response.send_message("I don't have permission to add roles to this user.", ephemeral=True)
    except discord.HTTPException:
        await interaction.response.send_message("An error occurred while trying to mute the user.", ephemeral=True)

''' UNMUTE '''
@Bot.tree.command(name="unmute", description="Unmute a member in the server")
@app_commands.describe(member="The member to unmute")
@app_commands.checks.has_permissions(manage_roles=True)
async def unmute(interaction: discord.Interaction, member: discord.Member):
    muted_role = discord.utils.get(interaction.guild.roles, name="Muted")
    await member.remove_roles(muted_role)
    await interaction.response.send_message(f'{member.mention} has been unmuted.')


"""===============================================  PURGE SYSTEM  ================================================================="""

@Bot.tree.command(name="purge", description="clean a specified number of messages")
@app_commands.describe(
    amount="Number of messages to clear",
    user="clean messages from a specific user (optional)",
    bots="clean messages from bots (True/False, optional)",
    embeds="Clean messages with embeds (True/False, optional)"
)
@app_commands.checks.has_permissions(manage_messages=True)
async def purge(
    interaction: discord.Interaction, 
    amount: int, 
    user: discord.Member = None, 
    bots: bool = False, 
    embeds: bool = False
):
    await interaction.response.defer(ephemeral=True)
    
    def check_message(message):
        if user and message.author != user:
            return False
        if bots and not message.author.bot:
            return False
        if embeds and not message.embeds:
            return False
        return True
    
    deleted = await interaction.channel.purge(limit=amount, check=check_message)
    
    await interaction.followup.send(
        f'Cleared {len(deleted)} messages.'
        f'{f" From user: {user.mention}" if user else ""}'
        f'{" From bots" if bots else ""}'
        f'{" With embeds" if embeds else ""}',
        ephemeral=True
    )

"""=============================================== TIMEOUT ================================================================="""

@Bot.tree.command(name="timeout", description="Timeout a member for a specified duration")
@app_commands.describe(
    member="The member to timeout",
    duration="Duration of the timeout (e.g., 10m, 1h, 1d)",
    reason="Reason for the timeout"
)
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(interaction: discord.Interaction, member: discord.Member, duration: str, reason: str = None):
    # Parse the duration
    try:
        duration_delta = parse_duration(duration)
    except ValueError:
        await interaction.response.send_message("Invalid duration format. Use format like 10m, 1h, 1d.", ephemeral=True)
        return

    # Check if the duration is within allowed limits (max 28 days)
    if duration_delta > datetime.timedelta(days=28):
        await interaction.response.send_message("Timeout duration cannot exceed 28 days.", ephemeral=True)
        return

    # Apply the timeout
    try:
        await member.timeout(duration_delta, reason=reason)
        until_date = discord.utils.utcnow() + duration_delta
        await interaction.response.send_message(f"{member.mention} has been timed out until {until_date.strftime('%Y-%m-%d %H:%M:%S')} UTC. Reason: {reason}")
    except discord.Forbidden:
        await interaction.response.send_message("I don't have permission to timeout this user.", ephemeral=True)
    except discord.HTTPException:
        await interaction.response.send_message("An error occurred while trying to timeout the user.", ephemeral=True)

def parse_duration(duration: str) -> datetime.timedelta:
    """Parse a duration string into a timedelta object."""
    unit = duration[-1].lower()
    try:
        value = int(duration[:-1])
    except ValueError:
        raise ValueError("Invalid duration format")

    if unit == 'm':
        return datetime.timedelta(minutes=value)
    elif unit == 'h':
        return datetime.timedelta(hours=value)
    elif unit == 'd':
        return datetime.timedelta(days=value)
    else:
        raise ValueError("Invalid duration unit")
    

''' UNTIMEOUT '''
@Bot.tree.command(name="untimeout", description="Remove timeout from a member")
@app_commands.describe(
    member="The member to remove timeout from",
    reason="Reason for removing the timeout"
)
@app_commands.checks.has_permissions(moderate_members=True)
async def untimeout(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    # Check if the member is timed out
    if member.is_timed_out():
        try:
            # Remove the timeout
            await member.timeout(None, reason=reason)
            await interaction.response.send_message(f"Timeout has been removed from {member.mention}. Reason: {reason}")
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to remove timeouts from this user.", ephemeral=True)
        except discord.HTTPException:
            await interaction.response.send_message("An error occurred while trying to remove the timeout.", ephemeral=True)
    else:
        await interaction.response.send_message(f"{member.mention} is not currently timed out.", ephemeral=True)


"""
""""============================================  KICK SYSTEM  =============================================================""""

@Bot.tree.command(name="kick", description="Kick a member from the server")
@app_commands.describe(member="The member to kick", reason="Reason for kicking")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    await member.kick(reason=reason)
    await interaction.response.send_message(f'{member.mention} has been kicked. Reason: {reason}')

""============================================  BAN AND UNBAN  =============================================================""

@Bot.tree.command(name="ban", description="Ban a member from the server")
@app_commands.describe(member="The member to ban", reason="Reason for banning")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    await member.ban(reason=reason)
    await interaction.response.send_message(f'{member.mention} has been banned. Reason: {reason}')

'''UNBAN'''
@Bot.tree.command(name="unban", description="Unban a member from the server")
@app_commands.describe(member="The member to unban (e.g., user#1234)")
@app_commands.checks.has_permissions(ban_members=True)
async def unban(interaction: discord.Interaction, member: str):
    banned_users = await interaction.guild.bans()
    member_name, member_discriminator = member.split('#')
    
    for ban_entry in banned_users:
        user = ban_entry.user
        if (user.name, user.discriminator) == (member_name, member_discriminator):
            await interaction.guild.unban(user)
            await interaction.response.send_message(f'Unbanned {user.mention}')
            return
    await interaction.response.send_message(f'User {member} not found in ban list.')
    """



"""===========================================  MEOW COMMAND  ============================================================="""

@Bot.command(aliases=["Meow"],
             help="Answers with Meow!",
             description="(prefix)meow to get a meow",
             brief="Answers with Meow!",
             enabled=True,
             hidden = False)
async def meow(ctx):
    await ctx.send("Meow!")



"""============================================= CAT FACTS =============================================================="""

@Bot.command(aliases=["cf"],
             help="Get a cat fact",
             description="(prefix)cf to get a cat fact",
             brief="Get a cat fact")
async def catfact(ctx):
    try:
        response = requests.get("https://catfact.ninja/fact")
        cat_fact = response.json().get("fact", "No fact available")
        await ctx.send(cat_fact)
    except Exception as e:
        print(f"Error fetching cat fact: {e}")
        await ctx.send("Sorry, I could not fetch a fact at this time.")


"""===========================================  CAT PICS  ============================================================="""

@Bot.command(aliases=["cp"],
             help="Get a cat picture",
             description="(prefix)cp to get a cat picture",
             brief="Get a cat picture")
async def nekopic(ctx):
    try:
        response = requests.get("https://api.thecatapi.com/v1/images/search")
        cat_image_url = response.json()[0].get("url", "No image available")
        await ctx.send(cat_image_url)
    except Exception as e:
        print(f"Error fetching cat image: {e}")
        await ctx.send("Sorry, I could not fetch a cat image at this time.")



"""===========================================  SAY COMMAND  ============================================================="""

@Bot.command(aliases=["speak", "echo"],
             help="Make the bot say something",
             description="(prefix)say message",
             brief="Make the bot say something")
async def say(ctx, *, args = "WHAT??"):
    await ctx.send("".join(args))



"""===========================================  ROLL COMMAND  ============================================================="""

@Bot.tree.command(name="roll", description="Roll a dice")
async def roll(interaction: discord.Interaction):
    result = random.randint(1, 6)
    await interaction.response.send_message(f"You rolled a {result}!")

"""===========================================  RANDOM COMMAND  ============================================================="""

@Bot.command(aliases=["rnd", "random"],
             help="Generate a random choice",
             description="(prefix)random item1 item2 item3......",
             brief="Generate a random choice")
async def Random(ctx, *args):
    await ctx.send(random.choice(args))

"""===========================================  GUESSING COMMAND  ============================================================="""

@Bot.tree.command(name="guess", description="Guess a number between 1 and 1000")
async def guess(interaction: discord.Interaction):
    number = random.randint(1, 1000)
    await interaction.response.send_message(f"I'm thinking of a number between 1 and 1000. Can you guess it?\n\nThe number was: {number}")


"""===========================================  CALCULATOR  ============================================================="""

@Bot.tree.command(name="calculator", description="Calculate two numbers")
@app_commands.describe(
    n1="First number",
    n2="Second number",
    operation="Operation to perform (+ - * / ^ %)"
)
async def calculator(interaction: discord.Interaction, n1: float, n2: float, operation: str):
    result = None
    error_message = None

    if operation == "+":
        result = n1 + n2
    elif operation == "-":
        result = n1 - n2
    elif operation == "*":
        result = n1 * n2
    elif operation == "/":
        if n2 != 0:
            result = n1 / n2
        else:
            error_message = "Cannot divide by zero"
    elif operation == "^":
        result = n1 ** n2
    elif operation == "%":
        if n2 != 0:
            result = n1 % n2
        else:
            error_message = "Cannot perform modulo with zero"
    else:
        error_message = "Invalid operation"

    if error_message:
        await interaction.response.send_message(error_message, ephemeral=True)
    else:
        await interaction.response.send_message(f"Result: {result}")
  

"""===========================================  JOINED COMMAND  ============================================================="""

@Bot.tree.command(name="joined", description="Show when a member joined the server")
@app_commands.describe(member="The member to check")
async def joined(interaction: discord.Interaction, member: discord.Member):
    join_date = member.joined_at.strftime("%Y-%m-%d %H:%M:%S UTC") if member.joined_at else "Unknown"
    await interaction.response.send_message(f"{member.mention} joined the server on {join_date}")


"""===========================================  SLAP COMMAND  ============================================================="""

class Slapper(commands.Converter):
    use_nicknames = bool
    def __init__(self,*, use_nicknames):
        self.use_nicknames = use_nicknames
    async def convert(self, ctx, argument):
            someone = ctx.message.mentions[0].display_name
            nickname = ctx.author.display_name
            if argument:  # Check if an argument is given
                if self.use_nicknames:
                    nickname = ctx.author.display_name
                someone = ctx.message.mentions[0].display_name
                return f"{nickname} slapped {someone} with {argument}"

            else:
                if self.use_nicknames:
                    nickname = ctx.author.display_name
                    someone = ctx.message.mentions[0].display_name
                    return f"{nickname} slapped {someone}"
@Bot.command(help="Slap someone",
             description="(prefix)slap item @member",
             brief="Slap someone",
             arguments=True)
async def slap(ctx, who : Slapper(use_nicknames=True)):
    await ctx.send(who)

@Bot.tree.command(name="slap", description="Slap someone with an optional item")
@app_commands.describe(
    victim="The user to slap",
    item="The item to slap with (optional)"
)
async def slap(interaction: discord.Interaction, victim: discord.Member, item: str = None):
    nickname = interaction.user.display_name

    if item:
        slap_message = f"{nickname} slapped {victim.mention} with {item}"
    else:
        slap_message = f"{nickname} slapped {victim.mention}"

    await interaction.response.send_message(slap_message)


"""===============================================  MUSIC SYSTEM  ================================================================="""

songs = asyncio.Queue()
play_next_song = asyncio.Event()

'''YTDL OPTIONS'''
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'force-ipv4': True,
    'preferredcodec': 'mp3',
    'buffersize': 256*1024,
}

'''ffmpeg OPTIONS'''
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -bufsize 256k'  
}
ytdl = yt_dlp.YoutubeDL(ytdl_format_options)


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Define the YTDLSource class
class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        
        if 'entries' in data:
            # Take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


'''SAFE DISCONNECT'''
async def safe_disconnect(voice_client):
    try:
        await voice_client.disconnect()
    except Exception as e:
        print(f"Error disconnecting: {e}")


""" JOIN """
@Bot.tree.command(name="join", description="Join the user's voice channel")
async def join(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    
    if not interaction.user.voice:
        await interaction.followup.send("You need to be in a voice channel to use this command.")
        return

    permissions = interaction.user.voice.channel.permissions_for(interaction.guild.me)
    if not permissions.connect or not permissions.speak:
        await interaction.followup.send("I don't have permission to join or speak in your voice channel.")
        return

    if interaction.guild.voice_client:
        if interaction.guild.voice_client.channel == interaction.user.voice.channel:
            await interaction.followup.send("I'm already in your voice channel.")
        else:
            await interaction.guild.voice_client.move_to(interaction.user.voice.channel)
            await interaction.followup.send(f"Moved to {interaction.user.voice.channel.mention}")
    else:
        await interaction.user.voice.channel.connect()
        await interaction.guild.change_voice_state(channel=interaction.guild.voice_client.channel, self_deaf=True)
        await interaction.followup.send(f"Joined {interaction.user.voice.channel.mention}")


''' PLAY SPOTIFY '''
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET))

# Update the play function to support Spotify
@Bot.tree.command(name="play_spotify", description="Play music from YouTube, Spotify, or a search term")
@app_commands.describe(query="The YouTube URL, Spotify URL, or search term")
async def play_spotify(interaction: discord.Interaction, query: str):
    await interaction.response.defer(thinking=True)
    
    # Check if the user is in a voice channel
    if not interaction.user.voice:
        await interaction.followup.send("You need to be in a voice channel to use this command.")
        return

    # Check if the bot has permission to join and speak in the voice channel
    permissions = interaction.user.voice.channel.permissions_for(interaction.guild.me)
    if not permissions.connect or not permissions.speak:
        await interaction.followup.send("I don't have permission to join or speak in your voice channel.")
        return

    # Join the user's voice channel if not already in one
    if not interaction.guild.voice_client:
        voice_client = await interaction.user.voice.channel.connect()
        await interaction.guild.change_voice_state(channel=voice_client.channel, self_deaf=True)
    else:
        voice_client = interaction.guild.voice_client
        if not interaction.guild.me.voice.self_deaf:
            await interaction.guild.change_voice_state(channel=voice_client.channel, self_deaf=True)

    try:
        if 'open.spotify.com' in query:
            # Handle Spotify URL
            track_id = query.split('/')[-1].split('?')[0]
            track_info = sp.track(track_id)
            search_query = f"{track_info['name']} {' '.join([artist['name'] for artist in track_info['artists']])}"
            results = VideosSearch(search_query, limit=1).result()
            if not results['result']:
                await interaction.followup.send("No results found for the Spotify track.")
                return
            url = f"https://www.youtube.com/watch?v={results['result'][0]['id']}"
        elif not query.startswith('http'):
            # Handle search term
            results = VideosSearch(query, limit=1).result()
            if not results['result']:
                await interaction.followup.send("No results found.")
                return
            url = f"https://www.youtube.com/watch?v={results['result'][0]['id']}"
        else:
            # Handle YouTube URL
            url = query

        player = await YTDLSource.from_url(url, loop=Bot.loop, stream=True)
        await songs.put((player, interaction.channel))

        if not voice_client.is_playing():
            await play_next(interaction.guild)
            await interaction.followup.send(f'Now playing: {player.title}')
        else:
            await interaction.followup.send(f'Added to queue: {player.title}')
    except Exception as e:
        logging.error(f"Error in play command: {e}")
        await interaction.followup.send(f"An error occurred: {str(e)}")

""" PLAY """
@Bot.tree.command(name="play", description="Play music from a YouTube URL or search term")
@app_commands.describe(query="The YouTube URL or search term")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer(thinking=True)
    
    # Check if the user is in a voice channel
    if not interaction.user.voice:
        await interaction.followup.send("You need to be in a voice channel to use this command.")
        return

    # Check if the bot has permission to join and speak in the voice channel
    permissions = interaction.user.voice.channel.permissions_for(interaction.guild.me)
    if not permissions.connect or not permissions.speak:
        await interaction.followup.send("I don't have permission to join or speak in your voice channel.")
        return

    # Join the user's voice channel if not already in one
    if not interaction.guild.voice_client:
        voice_client = await interaction.user.voice.channel.connect()
        await interaction.guild.change_voice_state(channel=voice_client.channel, self_deaf=True)
    else:
        voice_client = interaction.guild.voice_client
        if not interaction.guild.me.voice.self_deaf:
            await interaction.guild.change_voice_state(channel=voice_client.channel, self_deaf=True)

    try:
        if not query.startswith('http'):
            results = VideosSearch(query, limit=1).result()
            if not results['result']:
                await interaction.followup.send("No results found.")
                return
            url = f"https://www.youtube.com/watch?v={results['result'][0]['id']}"
        else:
            url = query

        player = await YTDLSource.from_url(url, loop=Bot.loop, stream=True)
        await songs.put((player, interaction.channel))

        if not voice_client.is_playing():
            await play_next(interaction.guild)
            await interaction.followup.send(f'Now playing: {player.title}')
        else:
            await interaction.followup.send(f'Added to queue: {player.title}')
    except Exception as e:
        logging.error(f"Error in play command: {e}")
        await interaction.followup.send(f"An error occurred: {str(e)}")

'''play_next'''
async def play_next(guild):
    global current_song
    if songs.empty():
        current_song = None
        return

    current_song, channel = await songs.get()
    voice_client = guild.voice_client
    if voice_client:
        def after_playing(error):
            Bot.loop.call_soon_threadsafe(play_next_song.set)
            if error:
                asyncio.run_coroutine_threadsafe(channel.send(f"An error occurred: {error}"), Bot.loop)

        voice_client.play(current_song, after=after_playing)
        await channel.send(f'Now playing: {current_song.title}')

    await play_next_song.wait()
    play_next_song.clear()

    await play_next(guild)


""" PAUSE """
@Bot.tree.command(name="pause", description="Pause the currently playing music")
async def pause(interaction: discord.Interaction):
    if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
        interaction.guild.voice_client.pause()
        await interaction.response.send_message("Paused the music.")
    else:
        await interaction.response.send_message("There's no music playing to pause.")


""" RESUME """
@Bot.tree.command(name="resume", description="Resume the paused music")
async def resume(interaction: discord.Interaction):
    if interaction.guild.voice_client and interaction.guild.voice_client.is_paused():
        interaction.guild.voice_client.resume()
        await interaction.response.send_message("Resumed the music.")
    else:
        await interaction.response.send_message("There's no paused music to resume.")


    """ QUEUE """
@Bot.tree.command(name="queue", description="Display the current song queue")
async def queue(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    if songs.empty() and not current_song:
        await interaction.followup.send("The queue is empty.")
    else:
        queue_list = []
        if current_song:
            queue_list.append(f"Currently playing: {current_song.title}")
        queue_copy = list(songs._queue)
        for i, (song, _) in enumerate(queue_copy, start=1):
            queue_list.append(f"{i}. {song.title}")
        await interaction.followup.send("\n".join(queue_list))


""" REMOVE """
@Bot.tree.command(name="remove", description="Remove a song from the queue")
@app_commands.describe(index="The position of the song in the queue (starting from 1)")
async def remove(interaction: discord.Interaction, index: int):
    await interaction.response.defer(thinking=True)
    
    if songs.empty():
        await interaction.followup.send("The queue is empty.")
        return

    if index < 1 or index > songs.qsize():
        await interaction.followup.send("Invalid song index.")
        return

    # Convert queue to list, remove the song, then recreate the queue
    queue_list = list(songs._queue)
    removed_song, _ = queue_list.pop(index - 1)
    
    # Clear the current queue and add back the songs
    songs._queue.clear()
    for song in queue_list:
        await songs.put(song)

    await interaction.followup.send(f"Removed '{removed_song.title}' from the queue.")


""" VOLUME """
@Bot.tree.command(name="volume", description="Change the volume of the music")
@app_commands.describe(volume="Volume level (0-100)")
async def volume(interaction: discord.Interaction, volume: int):
    await interaction.response.defer(thinking=True)
    if interaction.guild.voice_client is None:
        await interaction.followup.send("Not connected to a voice channel.")
        return
    
    if 0 <= volume <= 100:
        interaction.guild.voice_client.source.volume = volume / 100
        await interaction.followup.send(f"Changed volume to {volume}%")
    else:
        await interaction.followup.send("Volume must be between 0 and 100.")


""" SKIP """
@Bot.tree.command(name="skip", description="Skip the currently playing song")
async def skip(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    if not interaction.guild.voice_client or not interaction.guild.voice_client.is_playing():
        await interaction.followup.send("There's no song playing to skip.")
        return
    # Stop the current song
    interaction.guild.voice_client.stop()
    # Check if there are more songs in the queue
    if songs.empty():
        await interaction.followup.send("Skipped the current song. The queue is now empty.")
    else:
        # The play_next function will automatically play the next song
        await interaction.followup.send("Skipped the current song. Playing the next song in the queue.")

    # Trigger play_next
    Bot.loop.call_soon_threadsafe(play_next_song.set)


"""STOP"""
@Bot.tree.command(name="stop", description="Stop playing music and clear the queue")
async def stop(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        while not songs.empty():
            await songs.get()
        global current_song
        current_song = None
        await interaction.followup.send("Stopped the music and cleared the queue.")
    else:
        await interaction.followup.send("The bot is not connected to a voice channel.")


"""===========================================  GIF COMMAND  ============================================================="""

@Bot.tree.command(name="gif", description="Send a GIF based on a search term")
@app_commands.describe(search_term="The term to search for")
async def gif(interaction: discord.Interaction, search_term: str):
    await interaction.response.defer()  # Defer the response as the API call might take some time

    try:
        # Make a request to the GIPHY API
        url = f"https://api.giphy.com/v1/gifs/search?api_key={GIPHY_API_KEY}&q={search_term}&limit=25&rating=g"
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        data = response.json()

        if "data" in data and len(data["data"]) > 0:
            # Randomly select a GIF from the results
            gif_url = random.choice(data["data"])["images"]["original"]["url"]
            await interaction.followup.send(gif_url)
        else:
            await interaction.followup.send(f"Sorry, I couldn't find any GIFs for '{search_term}'.")
    
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            await interaction.followup.send("Sorry, there was an authentication error with the GIF service. Please contact the bot administrator.")
            print(f"GIPHY API authentication error: Invalid or expired API key")
        else:
            await interaction.followup.send(f"Sorry, there was an error connecting to the GIF service. Please try again later.")
            print(f"Error fetching GIF: {e}")
    
    except requests.exceptions.RequestException as e:
        await interaction.followup.send(f"Sorry, there was an error connecting to the GIF service. Please try again later.")
        print(f"Error fetching GIF: {e}")
    
    except json.JSONDecodeError as e:
        await interaction.followup.send(f"Sorry, there was an error processing the GIF data. Please try again later.")
        print(f"Error decoding JSON: {e}")
    
    except Exception as e:
        await interaction.followup.send(f"An unexpected error occurred. Please try again later.")
        print(f"Unexpected error in gif command: {e}")


"""===========================================  JOKE COMMAND  ============================================================="""

@Bot.tree.command(name="joke", description="Get a random joke")
async def joke(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    
    async with aiohttp.ClientSession() as session:
        async with session.get("https://official-joke-api.appspot.com/random_joke") as response:
            if response.status == 200:
                joke_data = await response.json()
                setup = joke_data['setup']
                punchline = joke_data['punchline']
                await interaction.followup.send(f"{setup}\n\n||{punchline}||")
            else:
                await interaction.followup.send("Sorry, I couldn't fetch a joke at the moment. Try again later!")


"""===========================================  SV STATS  ============================================================="""

@Bot.tree.command(name="serverstats", description="Display server statistics (Admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def serverstats(interaction: discord.Interaction):
    guild = interaction.guild
    
    # Collect server statistics
    total_members = guild.member_count
    online_members = sum(member.status != discord.Status.offline for member in guild.members)
    text_channels = len(guild.text_channels)
    voice_channels = len(guild.voice_channels)
    categories = len(guild.categories)
    roles = len(guild.roles)
    emojis = len(guild.emojis)
    boost_level = guild.premium_tier
    boosters = guild.premium_subscription_count

    # Create an embed with the server statistics
    embed = discord.Embed(title=f"{guild.name} Server Statistics", color=discord.Color.blue())
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    
    embed.add_field(name="Members", value=f"Total: {total_members}\nOnline: {online_members}", inline=True)
    embed.add_field(name="Channels", value=f"Text: {text_channels}\nVoice: {voice_channels}\nCategories: {categories}", inline=True)
    embed.add_field(name="Roles", value=roles, inline=True)
    embed.add_field(name="Emojis", value=emojis, inline=True)
    embed.add_field(name="Boost Level", value=boost_level, inline=True)
    embed.add_field(name="Boosters", value=boosters, inline=True)
    
    embed.set_footer(text=f"Server ID: {guild.id} | Created on: {guild.created_at.strftime('%B %d, %Y')}")

    await interaction.response.send_message(embed=embed, ephemeral=True)


"""===========================================  BOT INFO  ============================================================="""

bot_start_time = time.time()

@Bot.tree.command(name="botinfo", description="Display information about the bot (Admin only)")
@app_commands.checks.has_permissions(administrator=True)
async def botinfo(interaction: discord.Interaction):
    # Calculate uptime
    uptime = time.time() - bot_start_time
    days, remainder = divmod(int(uptime), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    # Get system info
    cpu_usage = psutil.cpu_percent()
    memory_usage = psutil.virtual_memory().percent
    
    # Create embed
    embed = discord.Embed(title="Bot Information", color=discord.Color.blue())
    embed.set_thumbnail(url=Bot.user.avatar.url if Bot.user.avatar else None)
    
    # Bot info
    embed.add_field(name="Bot Name", value=Bot.user.name, inline=True)
    embed.add_field(name="Bot ID", value=Bot.user.id, inline=True)
    embed.add_field(name="Created On", value=Bot.user.created_at.strftime("%B %d, %Y"), inline=True)
    
    # System info
    embed.add_field(name="Python Version", value=platform.python_version(), inline=True)
    embed.add_field(name="Discord.py Version", value=discord.__version__, inline=True)
    embed.add_field(name="Operating System", value=f"{platform.system()} {platform.release()}", inline=True)
    
    # Performance info
    embed.add_field(name="CPU Usage", value=f"{cpu_usage}%", inline=True)
    embed.add_field(name="Memory Usage", value=f"{memory_usage}%", inline=True)
    embed.add_field(name="Latency", value=f"{round(Bot.latency * 1000)}ms", inline=True)
    
    # Bot stats
    embed.add_field(name="Servers", value=len(Bot.guilds), inline=True)
    embed.add_field(name="Users", value=sum(guild.member_count for guild in Bot.guilds), inline=True)
    embed.add_field(name="Commands", value=len(Bot.tree.get_commands()), inline=True)
    
    # Uptime
    embed.add_field(name="Uptime", value=f"{days}d {hours}h {minutes}m {seconds}s", inline=False)
    
    # Set footer
    embed.set_footer(text="Bot developed by Your Name | Powered by discord.py")
    
    await interaction.response.send_message(embed=embed , ephemeral=True)

@botinfo.error
async def botinfo_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("You don't have permission to use this command. Only administrators can access bot information.", ephemeral=True)
    else:
        await interaction.response.send_message(f"An error occurred: {str(error)}", ephemeral=True)

Bot.run(TOKEN)
