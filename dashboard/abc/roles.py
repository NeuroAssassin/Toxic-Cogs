from redbot.core import commands, checks
from redbot.core.utils.chat_formatting import box, humanize_list, inline
import discord

from dashboard.abc.abc import MixinMeta
from dashboard.abc.mixin import dashboard

from dashboard.baserpc import HUMANIZED_PERMISSIONS


class DashboardRolesMixin(MixinMeta):
    @checks.guildowner()
    @dashboard.group()
    async def roles(self, ctx: commands.Context):
        """Customize the roles that have permission to certain parts of the dashboard."""

    @roles.command()
    async def create(self, ctx: commands.Context, role: discord.Role, *permissions):
        """Register a new discord role to access certain parts of the dashboard."""
        roles = await self.config.guild(ctx.guild).roles()
        if role.id in [r["roleid"] for r in roles]:
            await ctx.send(
                f"That role is already registered. Please edit with `{ctx.prefix}dashboard roles edit`."
            )
            return
        assigning = []
        missing = []
        disallowed = await self.config.disallowedperms()
        for p in permissions:
            if p.lower() in HUMANIZED_PERMISSIONS and not p.lower() in disallowed:
                assigning.append(p.lower())
            else:
                missing.append(p)
        if assigning:
            async with self.config.guild(ctx.guild).roles() as data:
                data.append({"roleid": role.id, "perms": assigning})
            self.configcache[ctx.guild.id]["roles"].append({"roleid": role.id, "perms": assigning})
        else:
            await ctx.send("Failed to identify any permissions in list. Please try again.")
            return
        if await ctx.embed_requested():
            e = discord.Embed(
                title="Role Registered",
                description=(
                    f"**Permissions assigned**: {humanize_list(list(map(inline, assigning)))}\n"
                    f"**Permissions unidentified**: {humanize_list(list(map(inline, missing or ['None'])))}"
                ),
                color=(await ctx.embed_color()),
            )
            await ctx.send(embed=e)
        else:
            await ctx.send(
                f"**Role registered**```css\n"
                f"[Permissions assigned]: {humanize_list(assigning)}\n"
                f"[Permissions unidentified]: {humanize_list(missing or ['None'])}"
                "```"
            )

    @roles.command()
    async def edit(self, ctx: commands.Context, role: discord.Role, *permissions):
        """Edit the permissions registered with a registered role."""
        changing = []
        missing = []
        disallowed = await self.config.disallowedperms()
        for p in permissions:
            if p.lower() in HUMANIZED_PERMISSIONS and not p.lower() in disallowed:
                changing.append(p.lower())
            else:
                missing.append(p.lower())

        if not changing:
            await ctx.send("Failed to identify any permissions in list. Please try again.")
            return

        roles = await self.config.guild(ctx.guild).roles()
        try:
            ro = [ro for ro in roles if ro["roleid"] == role.id][0]
        except IndexError:
            return await ctx.send("That role is not registered.")

        del roles[roles.index(ro)]

        added = []
        removed = []
        for p in changing:
            if p in ro["perms"]:
                ro["perms"].remove(p)
                removed.append(p)
            else:
                ro["perms"].append(p)
                added.append(p)

        if not ro["perms"]:
            await ctx.send(
                f"Failed to edit role. If you wish to remove all permissions from the role, please use `{ctx.clean_prefix}dashboard roles delete`."
            )
            return

        roles.append(ro)
        await self.config.guild(ctx.guild).roles.set(roles)
        self.configcache[ctx.guild.id]["roles"] = roles

        if await ctx.embed_requested():
            e = discord.Embed(
                title="Successfully edited role",
                description=(
                    f"**Permissions added**: {humanize_list(list(map(inline, added or ['None'])))}\n"
                    f"**Permissions removed**: {humanize_list(list(map(inline, removed or ['None'])))}\n"
                    f"**Permissions unidentified**: {humanize_list(list(map(inline, missing or ['None'])))}\n"
                ),
                color=(await ctx.embed_color()),
            )
            await ctx.send(embed=e)
        else:
            await ctx.send(
                "**Successfully edited role**```css\n"
                f"[Permissions added]: {humanize_list(added or ['None'])}\n"
                f"[Permissions removed]: {humanize_list(removed or ['None'])}\n"
                f"[Permissions unidentified]: {humanize_list(missing or ['None'])}"
                "```"
            )

    @roles.command()
    async def delete(self, ctx: commands.Context, *, role: discord.Role):
        """Unregister a role from the dashboard."""
        roles = await self.config.guild(ctx.guild).roles()
        try:
            ro = [ro for ro in roles if ro["roleid"] == role.id][0]
        except IndexError:
            return await ctx.send("That role is not registered.")

        del roles[roles.index(ro)]
        await self.config.guild(ctx.guild).roles.set(roles)
        self.configcache[ctx.guild.id]["roles"] = roles

        await ctx.send("Successfully deleted role.")

    @roles.command(name="list")
    async def roles_list(self, ctx: commands.Context):
        """List roles registered with dashboard."""
        data = await self.config.guild(ctx.guild).roles()
        roles = [
            ctx.guild.get_role(role["roleid"]).mention
            for role in data
            if ctx.guild.get_role(role["roleid"])
        ]
        if not roles:
            return await ctx.send("No roles set.")
        e = discord.Embed(title="Registered roles", description="\n".join(roles), color=0x0000FF)
        await ctx.send(embed=e)

    @roles.command()
    async def info(self, ctx: commands.Context, *, role: discord.Role):
        """List permissions for a registered role."""
        roles = await self.config.guild(ctx.guild).roles()
        try:
            r = [ro for ro in roles if ro["roleid"] == role.id][0]
        except IndexError:
            return await ctx.send("That role is not registered.")

        description = ""
        disallowed = await self.config.disallowedperms()

        if await ctx.embed_requested():
            for perm in r["perms"]:
                if perm in disallowed:
                    continue
                description += f"{inline(perm.title())}: {HUMANIZED_PERMISSIONS[perm]}\n"
            e = discord.Embed(description=f"**Role {role.mention} permissions**\n", color=0x0000FF)
            e.description += description
            await ctx.send(embed=e)
        else:
            for perm in r["perms"]:
                if perm in disallowed:
                    continue
                description += f"[{perm.title()}]: {HUMANIZED_PERMISSIONS[perm]}\n"
            await ctx.send(f"**Role {role.name} permissions**```css\n{description}```")

    @roles.command()
    async def perms(self, ctx: commands.Context):
        """Displays permission keywords matched with humanized descriptions."""
        disallowed = await self.config.disallowedperms()
        if await ctx.embed_requested():
            e = discord.Embed(
                title="Dashboard permissions", description="", color=(await ctx.embed_color()),
            )
            for key, value in HUMANIZED_PERMISSIONS.items():
                if key in disallowed:
                    continue
                e.description += f"{inline(key.title())}: {value}\n"
            await ctx.send(embed=e)
        else:
            description = ""
            for key, value in HUMANIZED_PERMISSIONS.items():
                if key in disallowed:
                    continue
                description += f"[{key.title()}]: {value}\n"
            await ctx.send(f"**Dashboard permissions**```css\n{description}```")
