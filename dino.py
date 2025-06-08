import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Select, View
import os
import json
from dotenv import load_dotenv
from discord.ext.commands import has_permissions
import datetime

# Load environment variables from the .env file
load_dotenv()

# Get the bot token from the environment variable
TOKEN = os.getenv('DISCORD_TOKEN')

# Initialize bot
intents = discord.Intents.default()
intents.members = True  # Ensure the bot has permission to fetch members and roles
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Role Management (roles.json) ---
# Load roles data from the roles.json file
def load_roles():
    if os.path.exists("roles.json"):
        with open("roles.json", "r") as file:
            return json.load(file)
    return {}

# Save roles data to the roles.json file
def save_roles(data):
    with open("roles.json", "w") as file:
        json.dump(data, file, indent=4)

# Fetch roles for a specific server
def get_roles_for_guild(guild_id):
    roles_data = load_roles()
    return roles_data.get(str(guild_id), [])

# Update roles for a specific server
def update_roles_for_guild(guild_id, roles):
    roles_data = load_roles()
    roles_data[str(guild_id)] = roles
    save_roles(roles_data)

# --- User Role Tracking (user_roles.json) ---
# Load user role data from the user_roles.json file
def load_user_roles():
    if os.path.exists("user_roles.json"):
        with open("user_roles.json", "r") as file:
            return json.load(file)
    return {}

# Save user role data to the user_roles.json file
def save_user_roles(data):
    with open("user_roles.json", "w") as file:
        json.dump(data, file, indent=4)

# Get the role a user currently has from the managed roles
def get_user_current_managed_role(guild_id, user_id):
    user_roles_data = load_user_roles()
    return user_roles_data.get(str(guild_id), {}).get(str(user_id))

# Set the role a user currently has from the managed roles
def set_user_current_managed_role(guild_id, user_id, role_id):
    user_roles_data = load_user_roles()
    if str(guild_id) not in user_roles_data:
        user_roles_data[str(guild_id)] = {}
    user_roles_data[str(guild_id)][str(user_id)] = role_id
    save_user_roles(user_roles_data)

# Clear the user's current managed role (e.g., if they no longer have any)
def clear_user_current_managed_role(guild_id, user_id):
    user_roles_data = load_user_roles()
    if str(guild_id) in user_roles_data and str(user_id) in user_roles_data[str(guild_id)]:
        del user_roles_data[str(guild_id)][str(user_id)]
        save_user_roles(user_roles_data)

# --- Birthday Management (birthdays.json) ---
# Load birthday data from the birthdays.json file
def load_birthdays():
    if os.path.exists("birthdays.json"):
        with open("birthdays.json", "r") as file:
            return json.load(file)
    return {}

# Save birthday data to the birthdays.json file
def save_birthdays(data):
    with open("birthdays.json", "w") as file:
        json.dump(data, file, indent=4)

# Get birthday embed details for a guild
def get_birthday_embed_info(guild_id):
    birthdays_data = load_birthdays()
    return birthdays_data.get(str(guild_id), {}).get("embed_info")

# Set birthday embed details for a guild
def set_birthday_embed_info(guild_id, channel_id, message_id):
    birthdays_data = load_birthdays()
    if str(guild_id) not in birthdays_data:
        birthdays_data[str(guild_id)] = {}
    birthdays_data[str(guild_id)]["embed_info"] = {"channel_id": channel_id, "message_id": message_id}
    save_birthdays(birthdays_data)

# Get a user's birthday
def get_user_birthday(guild_id, user_id):
    birthdays_data = load_birthdays()
    return birthdays_data.get(str(guild_id), {}).get("users", {}).get(str(user_id))

# Set a user's birthday
def set_user_birthday(guild_id, user_id, birthday):
    birthdays_data = load_birthdays()
    if str(guild_id) not in birthdays_data:
        birthdays_data[str(guild_id)] = {"users": {}}
    if "users" not in birthdays_data[str(guild_id)]:
        birthdays_data[str(guild_id)]["users"] = {}
    birthdays_data[str(guild_id)]["users"][str(user_id)] = birthday
    save_birthdays(birthdays_data)

# Get the birthday channel ID for a guild
def get_birthday_channel_id(guild_id):
    birthdays_data = load_birthdays()
    return birthdays_data.get(str(guild_id), {}).get("birthday_channel_id")

# Set the birthday channel ID for a guild
def set_birthday_channel_id(guild_id, channel_id):
    birthdays_data = load_birthdays()
    if str(guild_id) not in birthdays_data:
        birthdays_data[str(guild_id)] = {}
    birthdays_data[str(guild_id)]["birthday_channel_id"] = channel_id
    save_birthdays(birthdays_data)


# --- Bot Events and Commands ---
@bot.event
async def on_ready():
    print(f"Bot is logged in as {bot.user}")        
    await bot.tree.sync()
    print(f'Logged in as {bot.user}')

@bot.tree.command(name="roles", description="Switch between server roles")
async def roles(interaction: discord.Interaction):
    # Fetch all roles from the server stored in roles.json
    guild_id = interaction.guild.id
    roles = get_roles_for_guild(guild_id)

    if not roles:
        await interaction.response.send_message("No roles are available to switch to.", ephemeral=True)
        return

    # Prepare options for the dropdown
    options = [
        discord.SelectOption(
            label=role['name'], 
            value=str(role['id']), 
            emoji=None
        )
        for role in roles
    ]
    
    # Create the dropdown
    select = Select(
        placeholder="Choose a role to switch to",
        options=options
    )

    async def select_callback(interaction: discord.Interaction):
        role_id_new = int(select.values[0])  # Get the selected role ID
        member = interaction.user
        guild_id = interaction.guild.id
        
        # Get the new role object
        new_role = discord.utils.get(interaction.guild.roles, id=role_id_new)
        
        if not new_role:
            await interaction.response.send_message("The selected role was not found on this server.", ephemeral=True)
            return

        # Get the user's previously assigned managed role
        previous_managed_role_id = get_user_current_managed_role(guild_id, member.id)
        previous_managed_role = None
        if previous_managed_role_id:
            previous_managed_role = discord.utils.get(interaction.guild.roles, id=previous_managed_role_id)

        # Check if the user already has the new role
        if new_role in member.roles:
            # If they have it, remove it (toggle off)
            await member.remove_roles(new_role)
            # If the role being removed is the one we were tracking, clear it
            if previous_managed_role and previous_managed_role.id == new_role.id:
                clear_user_current_managed_role(guild_id, member.id)
            await interaction.response.send_message(f"Removed {new_role.name} from you.", ephemeral=True)
            return

        # If the user has a previous managed role and it's different from the new role
        if previous_managed_role and previous_managed_role.id != new_role.id:
            try:
                await member.remove_roles(previous_managed_role)
                remove_message = f"Removed previous role: {previous_managed_role.name}. "
            except discord.Forbidden:
                remove_message = "Could not remove previous role (permissions issue). "
            except Exception as e:
                remove_message = f"Error removing previous role: {e}. "
        else:
            remove_message = ""

        # Add the new role
        try:
            await member.add_roles(new_role)
            set_user_current_managed_role(guild_id, member.id, new_role.id)
            await interaction.response.send_message(f"{remove_message}Added {new_role.name} to you.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("Could not add the new role (permissions issue).", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error adding new role: {e}.", ephemeral=True)
    
    select.callback = select_callback
    view = View()
    view.add_item(select)
    
    await interaction.response.send_message("Please select a role from the dropdown:", view=view, ephemeral=True)

@bot.tree.command(name="add_role", description="Add a role to the role switch dropdown")
@has_permissions(manage_roles=True)  # Use manage_roles for moderator access
async def add_role(interaction: discord.Interaction, role: discord.Role):
    guild_id = interaction.guild.id
    roles = get_roles_for_guild(guild_id)

    # Check if the role is already added
    if any(r['id'] == role.id for r in roles):
        await interaction.response.send_message(f"{role.name} is already in the dropdown.", ephemeral=True)
        return

    # Add the new role to the roles list
    roles.append({"id": role.id, "name": role.name, "color": str(role.color)})
    update_roles_for_guild(guild_id, roles)
    
    await interaction.response.send_message(f"Added {role.name} to the dropdown.", ephemeral=True)

@bot.tree.command(name="remove_role", description="Remove a role from the role switch dropdown")
@has_permissions(manage_roles=True)  # Use manage_roles for moderator access
async def remove_role(interaction: discord.Interaction, role: discord.Role):
    guild_id = interaction.guild.id
    roles = get_roles_for_guild(guild_id)

    # Find and remove the role from the list
    role_to_remove = next((r for r in roles if r['id'] == role.id), None)
    if role_to_remove:
        roles.remove(role_to_remove)
        update_roles_for_guild(guild_id, roles)
        await interaction.response.send_message(f"Removed {role.name} from the dropdown.", ephemeral=True)
    else:
        await interaction.response.send_message(f"{role.name} is not in the dropdown.", ephemeral=True)

# --- Birthday Command Implementation ---

async def update_birthday_embed(guild: discord.Guild):
    """
    Fetches all birthdays, constructs the embed, and updates/sends the birthday embed message.
    """
    birthdays_data = load_birthdays()
    guild_birthdays = birthdays_data.get(str(guild.id), {}).get("users", {})
    embed_info = get_birthday_embed_info(guild.id)
    birthday_channel_id = get_birthday_channel_id(guild.id)

    if not birthday_channel_id:
        print(f"No birthday channel set for guild {guild.name}. Cannot update embed.")
        return # Cannot update if no channel is set

    target_channel = guild.get_channel(birthday_channel_id)
    if not target_channel:
        print(f"Configured birthday channel with ID {birthday_channel_id} not found in guild {guild.name}.")
        set_birthday_embed_info(guild.id, None, None) # Clear old embed info
        set_birthday_channel_id(guild.id, None) # Clear the channel ID too
        return # Cannot update if channel is gone

    # Sort birthdays by month and then day for consistent display
    sorted_birthdays = sorted(
        guild_birthdays.items(),
        key=lambda item: datetime.datetime.strptime(item[1], "%m/%d").strftime("%m%d")
    )

    description_lines = []
    for user_id_str, birthday in sorted_birthdays:
        try:
            member = await guild.fetch_member(int(user_id_str))
            # Changed from member.display_name to member.name (Discord username)
            description_lines.append(f"• **{member.name}**: {birthday}") 
        except discord.NotFound:
            # If user not found, remove from DB
            del guild_birthdays[user_id_str]
            save_birthdays(birthdays_data)
            print(f"Removed {user_id_str} from birthdays.json - user not found in guild.")
        except Exception as e:
            print(f"Error fetching member {user_id_str}: {e}")
            description_lines.append(f"• **Unknown User ({user_id_str})**: {birthday}")

    embed = discord.Embed(
        title="🎉 Server Birthdays 🎉",
        description="\n".join(description_lines) if description_lines else "No birthdays added yet!",
        color=discord.Color.blue()
    )

    if embed_info and embed_info.get("channel_id") == birthday_channel_id: # Only try to edit if existing embed is in the correct channel
        try:
            message = await target_channel.fetch_message(embed_info["message_id"])
            await message.edit(embed=embed)
            print(f"Updated birthday embed in channel {target_channel.name}")
        except discord.NotFound:
            print(f"Birthday embed message with ID {embed_info['message_id']} not found in channel {target_channel.name}. Sending new one.")
            # If message is not found, clear embed info and send a new one
            set_birthday_embed_info(guild.id, None, None)
            await send_initial_birthday_embed(guild)
        except discord.Forbidden:
            print(f"Missing permissions to edit message in channel {target_channel.name}.")
            # If forbidden, clear embed info and send a new one (permissions might have changed)
            set_birthday_embed_info(guild.id, None, None)
            await send_initial_birthday_embed(guild)
        except Exception as e:
            print(f"Error updating birthday embed: {e}. Sending new one.")
            set_birthday_embed_info(guild.id, None, None)
            await send_initial_birthday_embed(guild)
    else:
        # If no embed info, or embed info is for a different channel, send a new one
        await send_initial_birthday_embed(guild)


async def send_initial_birthday_embed(guild: discord.Guild):
    """Sends the initial birthday embed to the configured channel."""
    birthday_channel_id = get_birthday_channel_id(guild.id)
    if not birthday_channel_id:
        print(f"No birthday channel ID set for guild {guild.name}. Cannot send initial embed.")
        return

    target_channel = guild.get_channel(birthday_channel_id)
    if not target_channel:
        print(f"Configured birthday channel with ID {birthday_channel_id} not found in guild {guild.name}.")
        # Optionally, reset the channel ID if it's no longer valid
        set_birthday_channel_id(guild.id, None)
        return

    guild_birthdays = load_birthdays().get(str(guild.id), {}).get("users", {})
    description_lines = []

    # Sort birthdays by month and then day for consistent display
    sorted_birthdays = sorted(
        guild_birthdays.items(),
        key=lambda item: datetime.datetime.strptime(item[1], "%m/%d").strftime("%m%d")
    )
    
    for user_id_str, birthday in sorted_birthdays:
        try:
            member = await guild.fetch_member(int(user_id_str))
            # Changed from member.display_name to member.name (Discord username)
            description_lines.append(f"• **{member.name}**: {birthday}") 
        except discord.NotFound:
            pass # Handled in update_birthday_embed, but here for consistency if initial send is needed
        except Exception as e:
            print(f"Error fetching member {user_id_str} for initial embed: {e}")
            description_lines.append(f"• **Unknown User ({user_id_str})**: {birthday}")

    embed = discord.Embed(
        title="🎉 Server Birthdays 🎉",
        description="\n".join(description_lines) if description_lines else "No birthdays added yet!",
        color=discord.Color.blue()
    )

    try:
        message = await target_channel.send(embed=embed)
        set_birthday_embed_info(guild.id, target_channel.id, message.id)
        print(f"Sent initial birthday embed to channel {target_channel.name}")
    except discord.Forbidden:
        print(f"Missing permissions to send messages in channel {target_channel.name}.")
    except Exception as e:
        print(f"Error sending initial birthday embed: {e}")


@bot.tree.command(name="birthday", description="Add your birthday to the server's birthday list (MM/DD)")
@app_commands.describe(date="Your birthday in MM/DD format (e.g., 01/15 for January 15)")
async def birthday(interaction: discord.Interaction, date: str):
    user_id = interaction.user.id
    guild_id = interaction.guild.id

    # Check if the user has already submitted their birthday
    if get_user_birthday(guild_id, user_id):
        await interaction.response.send_message("You have already added your birthday. You can only set it once.", ephemeral=True)
        return

    # Validate date format (MM/DD)
    try:
        month, day = map(int, date.split('/'))
        if not (1 <= month <= 12 and 1 <= day <= 31): # Basic check, doesn't account for days in month
            raise ValueError
        # Use a dummy year to validate month/day combo
        datetime.datetime(2000, month, day) 
    except ValueError:
        await interaction.response.send_message("Invalid date format. Please use MM/DD (e.g., 01/15).", ephemeral=True)
        return

    # Store the birthday
    set_user_birthday(guild_id, user_id, date)
    await interaction.response.send_message(f"Your birthday ({date}) has been added! The birthday list will be updated.", ephemeral=True)

    # Update the birthday embed
    await update_birthday_embed(interaction.guild)

@bot.tree.command(name="set_birthday_channel", description="Set the channel where birthday messages will be sent.")
@has_permissions(manage_channels=True) # Requires manage channels permission to set this
@app_commands.describe(channel="The text channel for birthday messages.")
async def set_birthday_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = interaction.guild.id
    set_birthday_channel_id(guild_id, channel.id)
    await interaction.response.send_message(f"Birthday messages will now be sent to and updated in {channel.mention}.", ephemeral=True)
    
    # Immediately try to send/update the embed in the *new* channel.
    await update_birthday_embed(interaction.guild)

@bot.tree.command(name="birthday_help", description="Get help on how to use the birthday system.")
async def birthday_help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎂 Birthday System Help 🎂",
        description="Here's how to use the birthday feature on this server:",
        color=discord.Color.gold()
    )

    embed.add_field(
        name="1. Set the Birthday Channel (Moderators Only)",
        value=(
            "A server moderator needs to set up the dedicated channel where the birthday list will be displayed.\n"
            "Use the command: `/set_birthday_channel <#channel>`\n"
            "Example: `/set_birthday_channel #birthdays-list`"
        ),
        inline=False
    )

    embed.add_field(
        name="2. Add Your Birthday",
        value=(
            "Once the channel is set, you can add your birthday.\n"
            "Use the command: `/birthday <MM/DD>`\n"
            "Example: `/birthday 03/25` (for March 25th)\n\n"
            "**Important:** You can only set your birthday once!"
        ),
        inline=False
    )

    embed.add_field(
        name="3. See the Birthday List",
        value="After you add your birthday, it will automatically appear in the designated birthday channel, alongside everyone else's!",
        inline=False
    )

    await interaction.response.send_message(embed=embed)


# Run the bot with the token
bot.run(TOKEN)