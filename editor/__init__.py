from .editor import Editor


def setup(bot):
    bot.add_cog(Editor(bot))
