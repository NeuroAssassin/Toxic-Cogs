"""
MIT License

Copyright (c) 2018-Present NeuroAssassin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from typing import Union

import discord
from redbot.core import commands


class Editor(commands.Cog):
    """Allows for Administrators to edit a bot's messages by providing the new content or by copying another message"""

    def __init__(self, bot):
        self.bot = bot

    async def red_delete_data_for_user(self, **kwargs):
        """This cog does not store user data"""
        return

    @commands.command()
    @commands.admin()
    async def editmessage(
        self, ctx, ecid: int, editid: int, ccid: int, *, content: Union[int, str]
    ):
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
            return await ctx.send(
                "You provided an ID of a message to copy from, but didn't provide a channel ID to get the message from."
            )

        # Make sure channels and IDs are all good
        editchannel = self.bot.get_channel(ecid)
        if not editchannel or not type(editchannel) == discord.TextChannel:
            return await ctx.send("Invalid channel for the message you are editing.")
        if not editchannel.permissions_for(ctx.author).manage_messages and not (
            await self.bot.is_owner(ctx.author)
        ):
            return await ctx.send("You do not have permission to edit messages in that channel.")
        try:
            editmessage = await editchannel.fetch_message(editid)
        except discord.NotFound:
            return await ctx.send(
                "Invalid editing message ID, or you passed the wrong channel ID for the message."
            )
        except discord.Forbidden:
            return await ctx.send(
                "I'm not allowed to view the channel which contains the message I am editing."
            )
        if ccid != 0 and type(content) == int:
            copychannel = self.bot.get_channel(ccid)
            if not copychannel or not type(editchannel) == discord.TextChannel:
                return await ctx.send("Invalid ID for channel of the message to copy from.")
            try:
                copymessage = await copychannel.fetch_message(content)
            except discord.NotFound:
                return await ctx.send(
                    "Invalid copying message ID, or you passed the wrong channel ID for the message."
                )
            except discord.Forbidden:
                return await ctx.send(
                    "I'm not allowed to view the channel of the message from which I am copying."
                )

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
            try:
                await editmessage.edit(content=content, embed=None)
                await ctx.send(f"Message successfully edited.  Jump URL: {editmessage.jump_url}")
            except discord.errors.Forbidden:
                await ctx.send("I can only edit my own messages.")
