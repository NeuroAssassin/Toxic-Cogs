from typing import Optional

from reacticket.extensions.abc import MixinMeta
from reacticket.extensions.mixin import settings


class ReacTicketUserSettingsMixin(MixinMeta):
    @settings.group()
    async def userpermissions(self, ctx):
        """Control the permissions that users have with their own tickets"""
        pass

    @userpermissions.command()
    async def usercanclose(self, ctx, yes_or_no: Optional[bool] = None):
        """Set whether users can close their own tickets or not."""
        if yes_or_no is None:
            yes_or_no = not await self.config.guild(ctx.guild).usercanclose()

        await self.config.guild(ctx.guild).usercanclose.set(yes_or_no)
        if yes_or_no:
            await ctx.send("Users can now close their own tickets.")
        else:
            await ctx.send("Only administrators can now close tickets.")

    @userpermissions.command()
    async def usercanmodify(self, ctx, yes_or_no: Optional[bool] = None):
        """Set whether users can add or remove additional users to their ticket."""
        if yes_or_no is None:
            yes_or_no = not await self.config.guild(ctx.guild).usercanmodify()

        await self.config.guild(ctx.guild).usercanmodify.set(yes_or_no)
        if yes_or_no:
            await ctx.send("Users can now add/remove other users to their own tickets.")
        else:
            await ctx.send("Only administrators can now add/remove users to tickets.")

    @userpermissions.command()
    async def usercanname(self, ctx, yes_or_no: Optional[bool] = None):
        """Set whether users can rename their tickets and associated channels."""
        if yes_or_no is None:
            yes_or_no = not await self.config.guild(ctx.guild).usercanname()

        await self.config.guild(ctx.guild).usercanname.set(yes_or_no)
        if yes_or_no:
            await ctx.send("Users can now rename their tickets and associated channels.")
        else:
            await ctx.send("Only administrators can now rename tickets and associated channels.")
