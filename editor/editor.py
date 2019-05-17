from redbot.core import commands, checks
from typing import Union
import discord

class Editor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @checks.admin()
    async def editmessage(self, ctx, ecid: int, editid: int, ccid: int, *, content: Union[int, str]):
        """Edits a message with the content of another message or the specified content.

        Arguments:
            - ecid: The ID of the channel of the message you are editing (Required)

            - editid: The ID of the message you are editing (Required)

            - ccid: The ID of the channel of the message you are copying from.  If you are giving the raw content yourself, pass 0 as the channel ID. (Optional)

            - content: The ID of the message that contains the contents of what you want the other message to become, or the new content of the message.  (Required, integer (for message id) or text (for new content)
            
        Examples:
        `[p]editmessage <edit_channel_id> <edit_message_id> <copy_channel_id> <copy_message_id>`
        `[p]editmessage <edit_channel_id> <edit_message_id> 0 New content here`

        Real Examples:
        `[p]editmessage 133251234164375552 578969593708806144 133251234164375552 578968157520134161`
        `[p]editmessage 133251234164375552 578969593708806144 0 ah bruh`
        """
        if isinstance(content, int) and ccid == 0:
            return await ctx.send("You provided an ID of a message to copy from, but didn't provide a channel ID to get the message from.")
        
        # Make sure channels and IDs are all good
        editchannel = self.bot.get_channel(ecid)
        if not editchannel:
            return await ctx.send("Invalid channel for the message you are editing.")
        try:
            editmessage = await editchannel.fetch_message(editid)
        except discord.NotFound:
            return await ctx.send("Invalid editing message ID, or you passed the wrong channel ID for the message.")
        if ccid != 0 and type(content) == int:
            copychannel = self.bot.get_channel(ccid)
            if not copychannel:
                return await ctx.send("Invalid ID for channel of the message to copy from.")
            try:
                copymessage = await copychannel.fetch_message(content)
            except discord.NotFound:
                return await ctx.send("Invalid copying message ID, or you passed the wrong channel ID for the message.")
            
            # All checks passed
            content = copymessage.content
            try:
                embed = copymessage.embeds[0]
            except IndexError:
                embed = None
            try:
                await editmessage.edit(content=content, embed=embed)
            except discord.errors.Forbidden:
                return await ctx.send("I can only edit my own messages.")
            await ctx.send(f"Message successfully edited.  Jump URL: {editmessage.jump_url}")
        else:
            await editmessage.edit(content=content)
            try:
                await ctx.send(f"Message successfully edited.  Jump URL: {editmessage.jump_url}")
            except discord.errors.Forbidden:
                return await ctx.send("I can only edit my own messages.")