from redbot.core import commands, Config, checks

BaseCog = getattr(commands, "Cog", object)

class NameChecker(BaseCog):
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=4526891723)

        default_server = {
            "auto": "False",
            "personalized": [],
            "action": "ban"
        }

        self.config.register_guild(**default_server)

    async def on_member_join(self, member):
        if await self.config.guild(member.guild).auto() == "True":
            for invalid in ["http://", "https://", ".com", ".gg", ".org", ".gov", ".net", ".edu", "www."]:
                if invalid.lower() in member.name.lower():
                    if await self.config.guild(member.guild).action().lower() == "ban":
                        await member.ban(reason="Auto-ban; contained url part in name")
                        return
                    elif await self.config.guild(member.guild).action().lower() == "kick":
                        await member.kick(reason="Auto-kick; contained url part in name")
                        return
                    elif await self.config.guild(member.guild).action().lower() == "warn":
                        try:
                            await member.send("Warning; you have a piece of a url in your name, and it must be changed.  Otherwise, the moderators of the guild may kick or ban you.  Proceed at your own risk")
                        except:
                            pass
            else:
                for invalid in await self.config.guild(member.guild).personalized():
                    if invalid.lower() in member.name.lower():
                        if await self.config.guild(member.guild).action().lower() == "ban":
                            await member.ban(reason="Ban; contained personalized part in name")
                            return
                        elif await self.config.guild(member.guild).action().lower() == "kick":
                            await member.kick(reason="Kick; contained personalized part in name")
                            return
                        elif await self.config.guild(member.guild).action().lower() == "warn":
                            try:
                                await member.send("Warning; you have a part of a disallowed phrase in your name, and it must be changed.  Otherwise, the moderators of the guild may kick or ban you.  Proceed at your own risk")
                            except:
                                pass
            print(member.name)
                                
    @checks.has_permissions(ban_members=True)
    @commands.command()
    async def settings(self, ctx, auto="False", action="ban", *set):
        if not (auto.lower() in ["true", "false"]):
            return await ctx.send("Invalid auto argument; must be true or false.")
        if not (action.lower() in ["ban", "kick", "warn"]):
            return await ctx.send("Invalid action argument; must be kick, ban or warn")
        await self.config.guild(ctx.guild).auto.set(auto)
        await self.config.guild(ctx.guild).action.set(action)
        await self.config.guild(ctx.guild).personalized.set(list(set))
        await ctx.send("Setting have been set")