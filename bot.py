import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio

# Regional indicator emojis for options A through T (up to 20 options)
REGIONAL_INDICATORS = [chr(0x1F1E6 + i) for i in range(20)]

class PollView(discord.ui.View):
    def __init__(self, options, timeout):
        super().__init__(timeout=timeout)
        self.options = options
        self.votes = {} # Stores user_id: option_index to prevent double voting

        # Dynamically create a button for each option (up to 20)
        for i, option in enumerate(options):
            button = discord.ui.Button(
                label=option[:80], # Discord limits button labels to 80 characters
                emoji=REGIONAL_INDICATORS[i], 
                custom_id=f"poll_{i}",
                style=discord.ButtonStyle.secondary
            )
            button.callback = self.make_callback(i)
            self.add_item(button)

    def make_callback(self, index):
        async def callback(interaction: discord.Interaction):
            # Record or update the user's vote
            self.votes[interaction.user.id] = index
            await interaction.response.send_message(
                f"Your vote for **{self.options[index]}** has been recorded! (You can click another option to change it)", 
                ephemeral=True
            )
        return callback

class PollBot(commands.Bot):
    def __init__(self):
        # Intents are required for the bot to function properly
        super().__init__(command_prefix="!", intents=discord.Intents.default())

    async def setup_hook(self):
        # Syncs slash commands to the server
        await self.tree.sync()

bot = PollBot()

@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user.name} and ready to make decisions!')

@bot.tree.command(name="poll", description="Create a dynamic poll with up to 20 options.")
@app_commands.describe(
    question="What is the group deciding on?",
    options_list="Comma-separated list of options (e.g., Pizza, Burgers, Tacos)",
    duration="How long the poll lasts in seconds"
)
async def poll(interaction: discord.Interaction, question: str, options_list: str, duration: int = 60):
    # Parse the comma-separated options
    options = [opt.strip() for opt in options_list.split(",") if opt.strip()]

    # Validation: Discord limits views to 25 buttons (5 rows of 5). We cap at 20.
    if len(options) < 2 or len(options) > 20:
        await interaction.response.send_message("⚠️ Please provide between 2 and 20 options separated by commas.", ephemeral=True)
        return

    # Create the interactive view
    view = PollView(options=options, timeout=duration)

    # Build the embed message
    embed = discord.Embed(title=f"📊 {question}", description=f"⏱️ **Poll ends in {duration} seconds!**\n\n", color=discord.Color.blurple())
    for i, opt in enumerate(options):
        embed.description += f"{REGIONAL_INDICATORS[i]} {opt}\n"

    # Send the poll
    await interaction.response.send_message(embed=embed, view=view)

    # Wait for the duration of the poll
    await asyncio.sleep(duration)

    # --- TALLY VOTES AND DETERMINE WINNER ---
    vote_counts = {i: 0 for i in range(len(options))}
    for user_id, option_index in view.votes.items():
        vote_counts[option_index] += 1

    max_votes = max(vote_counts.values())
    winners = [index for index, count in vote_counts.items() if count == max_votes]

    result_embed = discord.Embed(title=f"🏁 Results: {question}", color=discord.Color.green())

    # Handle Tie-Breakers and Winners
    if max_votes == 0:
        result_embed.description = "Silence... Nobody voted!"
        result_embed.color = discord.Color.red()
    elif len(winners) > 1:
        # Tie-breaker logic triggered!
        tied_options = ", ".join([f"**{options[i]}**" for i in winners])
        winner_index = random.choice(winners) # Rolling the digital die
        
        result_embed.description = (
            f"**It's a tie!** \nTied options: {tied_options} (with {max_votes} votes each).\n\n"
            f"🎲 **Rolling the digital die...**\n\n"
            f"🏆 The final winner is **{options[winner_index]}**!"
        )
        result_embed.color = discord.Color.gold()
    else:
        # Clear winner
        winner_index = winners[0]
        result_embed.description = f"🏆 The winner is **{options[winner_index]}** with {max_votes} votes!"

    # Disable buttons on the original message
    for child in view.children:
        child.disabled = True

    # Update original message and post results
    original_msg = await interaction.original_response()
    await original_msg.edit(view=view)
    await interaction.followup.send(embed=result_embed)

# Replace 'YOUR_BOT_TOKEN_HERE' with your actual Discord bot token
bot.run('YOUR_BOT_TOKEN_HERE') 