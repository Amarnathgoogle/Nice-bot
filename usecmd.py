import discord
from discord.ext import commands
import asyncio
from typing import List, Tuple

# Define the log channel ID as a constant
LOG_CHANNEL_ID = 1390359707922993384
# Define the auto-delete channel ID as a constant
AUTO_DELETE_CHANNEL_ID = 1393741584910254270

class UseCommandCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _read_whitelist(self):
        try:
            with open("whitelisted.txt", "r") as f:
                return [int(line.strip()) for line in f.readlines() if line.strip()]
        except FileNotFoundError:
            return []

    def _write_whitelist(self, whitelist):
        with open("whitelisted.txt", "w") as f:
            for user_id in whitelist:
                f.write(f"{user_id}\n")

    @commands.command(name='w')
    @commands.is_owner()
    async def whitelist_command(self, ctx, user_id: int):
        """Adds or removes a user from the whitelist."""
        whitelist = self._read_whitelist()
        
        if user_id in whitelist:
            whitelist.remove(user_id)
            self._write_whitelist(whitelist)
            await ctx.send(f"✅ User <@{user_id}> has been removed from the whitelist.")
        else:
            whitelist.append(user_id)
            self._write_whitelist(whitelist)
            await ctx.send(f"✅ User <@{user_id}> has been added to the whitelist.")

    @commands.command(name='use')
    async def use_command(self, ctx, user_id: int, count: int, *, message: str):
        original_target_id = user_id
        original_target_user = None
        
        try:
            original_target_user = await self.bot.fetch_user(original_target_id)
        except discord.NotFound:
            await ctx.send(f"Error: User with ID {original_target_id} not found.")
            return

        # Check for whitelisted users
        whitelist = self._read_whitelist()
        
        is_cmd_user_whitelisted = ctx.author.id in whitelist
        is_target_whitelisted = original_target_id in whitelist
        
        # Collect messages to be deleted later
        messages_to_delete = [ctx.message]
        
        # Scenario 1: Both cmd user and target are whitelisted
        if is_cmd_user_whitelisted and is_target_whitelisted:
            response_msg = await ctx.send("🥹 Meara dho dho baap\n😭 Meara dho dho baap\n\nMadrchod log whitelisted hoka be backchodi ker na hai")
            messages_to_delete.append(response_msg)
            
            # Deletion logic for this specific case
            await asyncio.sleep(15)
            for msg in messages_to_delete:
                try:
                    await msg.delete()
                except (discord.NotFound, discord.Forbidden):
                    pass
            return
            
        # Scenario 2: Only target is whitelisted
        if is_target_whitelisted:
            # Send the aggressive message to the channel
            whitelisted_response_msg = await ctx.send(f"<@{original_target_id}> baap hai who meara maderchod, bada aya spam ker na whala")
            messages_to_delete.append(whitelisted_response_msg)

            # Redirect the DM campaign to the user who used the command
            target_user = ctx.author
            is_whitelisted_redirect = True
            
            # Initial embed to confirm command redirection
            initial_embed = discord.Embed(
                description=f"DM campaign is starting for you, as the original target is whitelisted.",
                color=discord.Color.gold()
            )
            initial_embed_msg = await ctx.send(embed=initial_embed)
            messages_to_delete.append(initial_embed_msg)
            
        # Scenario 3: Neither or only cmd user is whitelisted
        else:
            target_user = original_target_user
            is_whitelisted_redirect = False
            
            # Initial embed to confirm command execution
            initial_embed = discord.Embed(
                description=f"DM campaign is starting for {target_user.name}...",
                color=discord.Color.gold()
            )
            initial_embed_msg = await ctx.send(embed=initial_embed)
            messages_to_delete.append(initial_embed_msg)

        # Prepare a list of tasks for all worker bots to send DMs
        dm_tasks = [self.send_dms(worker, target_user, count, message) for worker in self.bot.worker_bots]
        
        # Use asyncio.gather to run all tasks concurrently and collect results
        results = await asyncio.gather(*dm_tasks)

        # Aggregate the results
        total_sent = sum(result['sent'] for result in results)
        total_failed = sum(result['failed'] for result in results)

        # --- Part 1: Completion Embed in Command Channel ---

        # Ping the user outside of the embed
        completion_response = await ctx.send(f"**<@{ctx.author.id}>, your DM campaign is complete!**")
        messages_to_delete.append(completion_response)

        completion_embed = discord.Embed(
            title="DM Campaign Summary",
            description="The requested DM campaign has finished.",
            color=discord.Color.green() if total_failed == 0 else discord.Color.orange()
        )
        completion_embed.add_field(name="Target User", value=f"{target_user.mention}", inline=False)
        completion_embed.add_field(name="Message", value=message, inline=False)
        completion_embed.add_field(name="Requested Count", value=f"{count * len(self.bot.worker_bots)}", inline=False)
        completion_embed.add_field(name="DMs Sent", value=f"✅ {total_sent}", inline=True)
        completion_embed.add_field(name="DMs Failed", value=f"❌ {total_failed}", inline=True)

        completion_embed_msg = await ctx.send(embed=completion_embed)
        messages_to_delete.append(completion_embed_msg)

        # Deletion logic after the campaign is finished
        await asyncio.sleep(15)
        for msg in messages_to_delete:
            try:
                await msg.delete()
            except (discord.NotFound, discord.Forbidden):
                pass

        # --- Part 2: Detailed Log Embed in Logs Channel ---
        # Do not send logs if both users are whitelisted
        if not (is_cmd_user_whitelisted and is_target_whitelisted):
            log_channel = self.bot.get_channel(LOG_CHANNEL_ID)
            if log_channel:
                log_embed = discord.Embed(
                    title="DM Campaign Log",
                    description="Detailed log of a recently completed DM campaign.",
                    color=discord.Color.blue()
                )

                # Set user's global avatar as the author icon
                log_embed.set_author(name=f"{ctx.author.name} ({ctx.author.id})", icon_url=ctx.author.display_avatar.url)

                # Add fields for user and target info
                log_embed.add_field(name="**Commander**",
                                    value=f"**User:** {ctx.author.mention}\n**ID:** `{ctx.author.id}`\n**Server:** `{ctx.guild.name}`",
                                    inline=True)
                
                target_description = f"**User:** {target_user.mention}\n**ID:** `{target_user.id}`"
                if is_whitelisted_redirect:
                    target_description += f"\n*(Original target: {original_target_user.mention})*"
                log_embed.add_field(name="**Target**", value=target_description, inline=True)

                log_embed.add_field(name="**Message**", value=message, inline=False)
                log_embed.add_field(name="**Requested Count**", value=f"`{count * len(self.bot.worker_bots)}`", inline=False)

                # Add the "whitelisted" message if applicable
                if is_whitelisted_redirect:
                    log_embed.add_field(name="**Note**", value="DM campaign isshued coz tryed to dm whitelisted user", inline=False)

                # Create a detailed breakdown per bot
                breakdown_text = ""
                for result in results:
                    bot_user = self.bot.get_user(result['bot_id'])
                    if bot_user:
                        breakdown_text += f"- **{bot_user.name}**: Sent `✅ {result['sent']}` | Failed `❌ {result['failed']}`\n"
                    else:
                        breakdown_text += f"- **Bot ID `{result['bot_id']}`**: Sent `✅ {result['sent']}` | Failed `❌ {result['failed']}`\n"
                
                if len(breakdown_text) > 1024:
                    chunks = [breakdown_text[i:i+1000] for i in range(0, len(breakdown_text), 1000)]
                    log_embed.add_field(name="**DM Breakdown (Part 1)**", value=chunks[0], inline=False)
                    for i, chunk in enumerate(chunks[1:]):
                        log_embed.add_field(name=f"**DM Breakdown (Part {i+2})**", value=chunk, inline=False)
                else:
                    log_embed.add_field(name="**DM Breakdown**", value=breakdown_text, inline=False)

                log_embed.add_field(name="**Total Sent**", value=f"✅ `{total_sent}`", inline=True)
                log_embed.add_field(name="**Total Failed**", value=f"❌ `{total_failed}`", inline=True)

                # Set the target user's global avatar as the footer icon
                log_embed.set_footer(text=f"Target: {target_user.name} ({target_user.id})", icon_url=target_user.display_avatar.url)

                await log_channel.send(embed=log_embed)
            else:
                print(f"Error: Log channel with ID {LOG_CHANNEL_ID} not found.")

    async def send_dms(self, worker, user, count, message):
        sent_count = 0
        failed_count = 0
        for i in range(count):
            try:
                target = await worker.fetch_user(user.id)
                await target.send(message)
                sent_count += 1
            except discord.Forbidden:
                failed_count += 1
                break
            except Exception as e:
                print(f"An error occurred with worker {worker.user.id}: {e}")
                failed_count += 1
            await asyncio.sleep(0.1)

        return {'bot_id': worker.user.id, 'sent': sent_count, 'failed': failed_count}

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id == AUTO_DELETE_CHANNEL_ID and not message.author.bot:
            await asyncio.sleep(15)
            try:
                await message.delete()
            except discord.NotFound:
                pass
            except discord.Forbidden:
                print(f"Error: Missing permissions to delete message in channel {message.channel.id}.")
