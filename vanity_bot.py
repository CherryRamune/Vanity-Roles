import os

TOKEN = os.getenv("TOKEN")

import discord
from discord.ext import commands, tasks
from discord import app_commands

print("TOKEN LOADED:", TOKEN is not None)

DATA_FILE = "vanity_roles.json"

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        user_roles = json.load(f)
else:
    user_roles = {}


def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(user_roles, f, indent=4)


def is_valid_hex(color):
    return bool(re.fullmatch(r"#([0-9a-fA-F]{6})", color))


def sanitize_name(name):
    # Allow letters, numbers, spaces, and limited symbols — no mentions
    name = name.strip()
    if len(name) > 32:
        name = name[:32]
    # Very basic profanity guard placeholder (replace or expand if needed)
    banned = ["admin", "mod", "owner"]
    if any(word.lower() in name.lower() for word in banned):
        return None
    return name


async def get_or_create_vanity_role(member, name, color):
    guild = member.guild
    role_id = user_roles.get(str(member.id))
    existing_role = guild.get_role(role_id) if role_id else None

    if existing_role:
        await existing_role.edit(name=name, color=color, permissions=discord.Permissions.none())
        return existing_role

    new_role = await guild.create_role(
        name=name,
        color=color,
        permissions=discord.Permissions.none(),
        reason=f"Vanity role for {member}"
    )

    await new_role.edit(position=1)

    user_roles[str(member.id)] = new_role.id
    save_data()

    return new_role


@tasks.loop(minutes=10)
async def cleanup_missing_roles():
    for guild in bot.guilds:
        for user_id, role_id in list(user_roles.items()):
            role = guild.get_role(role_id)
            if role is None:  # role manually deleted
                del user_roles[user_id]
                save_data()


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print("Sync error:", e)
    cleanup_missing_roles.start()
    print(f"Logged in as {bot.user}")


# ===== SLASH COMMANDS ===== #

@bot.tree.command(name="vanity", description="Create or edit your vanity role.")
@app_commands.describe(
    name="The custom name for your vanity role.",
    color_hex="Color in hex format (example: #ff66cc)."
)
async def vanity(interaction: discord.Interaction, name: str, color_hex: str):
    member = interaction.user

    name = sanitize_name(name)
    if not name:
        await interaction.response.send_message("❌ Invalid role name. Try something simple.", ephemeral=True)
        return

    if not is_valid_hex(color_hex):
        await interaction.response.send_message("❌ Color must be a hex value like `#ff33cc`.", ephemeral=True)
        return

    color = discord.Color(int(color_hex[1:], 16))
    role = await get_or_create_vanity_role(member, name, color)

    if role not in member.roles:
        await member.add_roles(role, reason="Vanity role assignment")

    # Optional: Match nickname to vanity role name
    try:
        await member.edit(nick=name)
    except:
        pass  # no permissions to change nick — ignore

    await interaction.response.send_message(f"✅ Vanity role updated to **{name}** ({color_hex})", ephemeral=True)


@bot.tree.command(name="vanity_remove", description="Remove your vanity role completely.")
async def vanity_remove(interaction: discord.Interaction):
    member = interaction.user
    role_id = user_roles.get(str(member.id))
    role = member.guild.get_role(role_id) if role_id else None

    if role:
        await role.delete(reason="User removed vanity role.")
        del user_roles[str(member.id)]
        save_data()

    await interaction.response.send_message("✅ Your vanity role has been removed.", ephemeral=True)


@bot.tree.command(name="vanity_palette", description="Get recommended aesthetic color palettes.")
async def vanity_palette(interaction: discord.Interaction):
    colors = [
        "#ff9ed4  (Cherry Blossom)",
        "#ff6ec7  (Candy Pink)",
        "#a29bfe  (Lavender Dreams)",
        "#6af5ff  (Aqua Ice)",
        "#ffd95d  (Soft Gold)",
        "#9dffb3  (Mint Glow)"
    ]
    formatted = "\n".join(colors)
    await interaction.response.send_message(f"🎨 **Nice color ideas:**\n{formatted}", ephemeral=True)



bot.run(TOKEN)




