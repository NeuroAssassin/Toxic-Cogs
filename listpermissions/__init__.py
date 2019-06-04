from .listpermissions import ListPermissions


def setup(bot):
    bot.add_cog(ListPermissions(bot))
