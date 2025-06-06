import discord
from discord.ext import commands
from discord.ui import Button, View
import asyncio

TOKEN = 'MTM4MDE4ODQzMzYxNTY4Nzc1MA.G2Q6yC.t8TldrUX9H9NZBHAm1IOxjayElI1_tpoQ8TmIM'

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Config
VERIFY_ROLE_NAME = "Verified"
MOD_ROLES = ["Admin", "Mod"]
TICKET_CATEGORY_NAME = "📩 tickets"
IMAGE_ONLY_CHANNELS = ["📸︱stats-only"]
LOG_CHANNEL_NAME = "📄︱logs"
WELCOME_CHANNEL_NAME = "👋︱welcome"
JOIN_CHANNEL_NAME = "📥︱joins"

async def log_action(guild, message):
    log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
    if log_channel:
        await log_channel.send(message)

@bot.event
async def on_ready():
    print(f'✅ Bot is online as {bot.user.name}')

# ✅ Verify button
@bot.command()
@commands.has_permissions(administrator=True)
async def send_verify(ctx):
    button = Button(label="✅ Verify me", style=discord.ButtonStyle.success)

    async def button_callback(interaction):
        role = discord.utils.get(interaction.guild.roles, name=VERIFY_ROLE_NAME)
        if role:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("You're verified ✅", ephemeral=True)
            await log_action(interaction.guild, f"🔓 {interaction.user.mention} got verified.")
        else:
            await interaction.response.send_message("❌ Role not found.", ephemeral=True)

    button.callback = button_callback
    view = View(timeout=None)  # View never expires
    view.add_item(button)
    await ctx.send("🔒 Click the button to verify yourself:", view=view)

# 🎭 Role selection
@bot.command()
@commands.has_permissions(administrator=True)
async def send_roles(ctx):
    view = View(timeout=None)
    roles_map = {
        "👥 Play with others": "Matchmaker",
        "💬 Just Chat": "Chatter",
        "🤝 Play with Vinni": "PlayWithVinni",
        "🔥 Everything": "AllAccess",
        "🏆 Tournaments": "Tournaments"
    }

    async def make_callback(label, role_name):
        async def callback(interaction):
            member = interaction.user
            role = discord.utils.get(interaction.guild.roles, name=role_name)
            if not role:
                await interaction.response.send_message(f"❌ Role '{role_name}' not found.", ephemeral=True)
                return

            if role_name == "AllAccess":
                removed = []
                for r in roles_map.values():
                    if r != "AllAccess":
                        other = discord.utils.get(interaction.guild.roles, name=r)
                        if other and other in member.roles:
                            await member.remove_roles(other)
                            removed.append(other.name)
                await member.add_roles(role)
                await interaction.response.send_message(f"✅ AllAccess granted. Removed: {', '.join(removed)}", ephemeral=True)
                await log_action(interaction.guild, f"🎭 {member.mention} got AllAccess. Removed: {', '.join(removed)}")
            else:
                if role in member.roles:
                    await member.remove_roles(role)
                    await interaction.response.send_message(f"❎ Removed {role_name}.", ephemeral=True)
                    await log_action(interaction.guild, f"🎭 {member.mention} removed role {role_name}.")
                else:
                    all_access = discord.utils.get(interaction.guild.roles, name="AllAccess")
                    if all_access in member.roles:
                        await member.remove_roles(all_access)
                    await member.add_roles(role)
                    await interaction.response.send_message(f"✅ Added {role_name}.", ephemeral=True)
                    await log_action(interaction.guild, f"🎭 {member.mention} got role {role_name}.")

        return callback

    for label, role in roles_map.items():
        button = Button(label=label, style=discord.ButtonStyle.primary)
        button.callback = await make_callback(label, role)
        view.add_item(button)

    await ctx.send("🎯 Select your roles below. Click again to remove:", view=view)

# 🎟️ Ticket system
@bot.command()
@commands.has_permissions(administrator=True)
async def send_ticket(ctx):
    open_button = Button(label="🎟️ Open Ticket", style=discord.ButtonStyle.green)

    async def open_callback(interaction):
        guild = interaction.guild
        user = interaction.user
        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
        if not category:
            category = await guild.create_category(TICKET_CATEGORY_NAME)
            await log_action(guild, f"📁 Created category '{TICKET_CATEGORY_NAME}'.")

        ticket_name = f"ticket-{user.name}".lower().replace(" ", "-")
        existing = discord.utils.get(guild.text_channels, name=ticket_name)
        if existing:
            await interaction.response.send_message("❗ You already have an open ticket.", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        for role_name in MOD_ROLES:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(ticket_name, overwrites=overwrites, category=category)
        await channel.send(f"👋 Hi {user.mention}, thanks for reaching out!")

        close_button = Button(label="🔒 Close Ticket", style=discord.ButtonStyle.danger)

        async def close_callback(inter_close):
            closer = inter_close.user
            if not any(role.name in MOD_ROLES for role in closer.roles):
                await inter_close.response.send_message("⛔ Only staff can close tickets.", ephemeral=True)
                return
            await inter_close.response.send_message("✅ Ticket will be closed in 5 seconds...", ephemeral=True)
            await channel.send(f"📌 Ticket closed by {closer.mention}")
            await asyncio.sleep(5)
            await channel.delete()
            await log_action(guild, f"🔒 Ticket closed by {closer.mention}")

        close_button.callback = close_callback
        close_view = View(timeout=None)
        close_view.add_item(close_button)
        await channel.send("🧷 Staff can close this ticket below:", view=close_view)

        await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)

    open_button.callback = open_callback
    view = View(timeout=None)
    view.add_item(open_button)
    await ctx.send("📩 Need help? Open a ticket:", view=view)

# 📸 Image-only channels
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.name in IMAGE_ONLY_CHANNELS and not message.attachments:
        try:
            await message.delete()
            await message.channel.send(
                f"{message.author.mention} 🚫 Only images or clips are allowed here.",
                delete_after=5
            )
            await log_action(message.guild, f"🖼️ Deleted non-image from {message.author.mention} in #{message.channel.name}")
        except discord.Forbidden:
            print(f"⚠️ Missing permissions in {message.channel.name}")
        return

    await bot.process_commands(message)

# 👋 Welcome embed on join
@bot.event
async def on_member_join(member):
    guild = member.guild
    join_channel = discord.utils.get(guild.text_channels, name=JOIN_CHANNEL_NAME)

    if join_channel:
        embed = discord.Embed(
            title=f"📥 {member.name} just joined!",
            description=(
                f"Welcome to **vinni.bs**, {member.mention}! 🎉\n\n"
                "👉 Start by checking out:\n"
                "📜 Rules\n"
                "✅ Verify yourself\n"
                "🎭 Pick roles\n"
                "💬 Say hi in general chat\n\n"
                "Need help? Ask in #ask-me or open a ticket!"
            ),
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.avatar.url if member.avatar else guild.icon.url)
        await join_channel.send(embed=embed)
        await log_action(guild, f"👤 New member joined: {member.mention}")

# 📜 Rules embed
@bot.command()
@commands.has_permissions(administrator=True)
async def send_rules(ctx):
    if "rules" not in ctx.channel.name.lower():
        await ctx.send("⚠️ This command must be used in the rules channel.")
        return

    embed = discord.Embed(
        title="📜 Server Rules – vinni.bs",
        description=(
            "🚫 No toxicity, hate speech or bullying\n"
            "🔞 No NSFW content\n"
            "🔊 Keep voice chats clean and respectful\n"
            "📢 Don’t spam or flood channels\n"
            "🔗 No self-promotion (unless allowed by staff)\n"
            "🛠 Follow staff instructions at all times\n\n"
            "Violating these rules may result in timeouts, kicks or bans.\n\n"
            "✅ By verifying yourself, you agree to these rules."
        ),
        color=discord.Color.red()
    )
    embed.set_footer(text="Thanks for keeping the server clean and fun!")
    await ctx.send(embed=embed)

# 🎉 Welcome embed
@bot.command()
@commands.has_permissions(administrator=True)
async def send_welcome(ctx):
    if not WELCOME_CHANNEL_NAME in ctx.channel.name:
        await ctx.send("⚠️ This command can only be used in the welcome channel.")
        return

    guild = ctx.guild
    rules = discord.utils.find(lambda c: "rules" in c.name.lower(), guild.text_channels)
    verify = discord.utils.find(lambda c: "verify" in c.name.lower(), guild.text_channels)
    roles = discord.utils.find(lambda c: "role-select" in c.name.lower(), guild.text_channels)
    chat = discord.utils.find(lambda c: "general-chat" in c.name.lower(), guild.text_channels)
    ask = discord.utils.find(lambda c: "ask-me" in c.name.lower(), guild.text_channels)
    ticket = discord.utils.find(lambda c: "open-ticket" in c.name.lower(), guild.text_channels)

    if not all([rules, verify, roles, chat, ask, ticket]):
        await ctx.send("❌ One or more channels are missing or misnamed.")
        return

    embed = discord.Embed(
        title="🎉 Welcome to vinni.bs!",
        description=(
            "Welcome to the official Brawl Stars server by **Vinni** 🧠💥\n\n"
            "**Here’s what you can do:**\n"
            "✨ Share your stats\n"
            "🎮 Find teammates\n"
            "🏆 Join tournaments\n"
            "📢 Post clips & memes\n"
            "🔒 Use private voice calls\n"
            "...and play directly with **Vinni**!\n\n"
            "✅ **Start here:**\n"
            f"{rules.mention}, {verify.mention}, {roles.mention}, {chat.mention}\n\n"
            f"Need help? → {ask.mention} or open a ticket in {ticket.mention}\n"
            "Have fun – let's go! 🚀"
        ),
        color=discord.Color.blurple()
    )
    embed.set_thumbnail(url=guild.icon.url if guild.icon else discord.Embed.Empty)
    await ctx.send(embed=embed)

# Launch bot
bot.run(TOKEN)
