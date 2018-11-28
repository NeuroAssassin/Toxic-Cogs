"""This cog is mostly derived from Aikaterna's cog "chatchart"
You can find the cog here: https://github.com/aikaterna/aikaterna-cogs/tree/v3/chatchart"""

import discord
import heapq
import os
from io import BytesIO

import matplotlib
matplotlib.use('agg')

import matplotlib.pyplot as plt
plt.switch_backend('agg')

from redbot.core import commands

BaseCog = getattr(commands, "Cog", object)

class CommandChart(BaseCog):
    def __init__(self, bot):
        self.bot = bot

    def create_chart(self, top, others, channel):
        plt.clf()
        sizes = [x[1] for x in top]
        labels = ["{} {:g}%".format(x[0], x[1]) for x in top]
        if len(top) >= 20:
            sizes = sizes + [others]
            labels = labels + ["Others {:g}%".format(others)]
        if len(channel.name) >= 19:
            channel_name = "{}...".format(channel.name[:19])
        else:
            channel_name = channel.name
        title = plt.title("Stats in #{}".format(channel_name), color="white")
        title.set_va("top")
        title.set_ha("center")
        plt.gca().axis("equal")
        colors = [
            "r",
            "darkorange",
            "gold",
            "y",
            "olivedrab",
            "green",
            "darkcyan",
            "mediumblue",
            "darkblue",
            "blueviolet",
            "indigo",
            "orchid",
            "mediumvioletred",
            "crimson",
            "chocolate",
            "yellow",
            "limegreen",
            "forestgreen",
            "dodgerblue",
            "slateblue",
            "gray",
        ]
        pie = plt.pie(sizes, colors=colors, startangle=0)
        plt.legend(
            pie[0],
            labels,
            bbox_to_anchor=(0.7, 0.5),
            loc="center",
            fontsize=10,
            bbox_transform=plt.gcf().transFigure,
            facecolor="#ffffff",
        )
        plt.subplots_adjust(left=0.0, bottom=0.1, right=0.45)
        image_object = BytesIO()
        plt.savefig(image_object, format="PNG", facecolor="#36393E")
        image_object.seek(0)
        return image_object

    @commands.command()
    async def commandchart(self, ctx, channel: discord.TextChannel = None, number=5000):
        e = discord.Embed(description="Loading...", color=0x000099)
        e.set_thumbnail(url="https://i.imgur.com/vSp4xRk/gif")
        em = await ctx.send(embed=e)

        if channel is None:
            channel = ctx.message.channel
        if not channel.permissions_for(ctx.message.author).read_messages == True:
            await em.delete()
            return await ctx.send("You do not have the proper permissions to access that channel.")

        message_list = []
        command_list = []
        for x in self.bot.commands:
            command_list.append(x.name)
        print(command_list)
        try:
            async for msg in channel.history(limit=number):
                if msg.content.startswith(ctx.clean_prefix):
                    for command in command_list:
                        if msg.content[(len(ctx.clean_prefix)):].startswith(command):
                            message_list.append(msg.content[(len(ctx.clean_prefix)):])
        except discord.errors.Forbidden:
            await em.delete()
            return await ctx.send("I do not have permission to look at that channel.")
        msg_data = {"total count": 0, "commands": {}}

        for msg in message_list:
            if len(msg) >= 20:
                short_name = "{}...".format(msg[:20])
            else:
                short_name = msg
            if short_name in msg_data['commands']:
                msg_data['commands'][short_name]['count'] += 1
                msg_data['total count'] += 1
            else:
                msg_data['commands'][short_name] = {}
                msg_data['commands'][short_name]['count'] = 1
                msg_data['total count'] += 1
        
        if msg_data['commands'] == {}:
            await em.delete()
            return await ctx.send("No commands have been run in that channel.")
        for command in msg_data['commands']:
            pd = float(msg_data['commands'][command]['count']) / float(msg_data['total count'])
            msg_data['commands'][command]['percent'] = round(pd * 100, 1)

        top_ten = heapq.nlargest(
            20,
            [
                (x, msg_data['commands'][x][y])
                for x in msg_data['commands']
                for y in msg_data['commands'][x]
                if y == 'percent'
            ],
            key=lambda x: x[1],
        )
        others = 100 - sum(x[1] for x in top_ten)
        img = self.create_chart(top_ten, others, channel)
        await em.delete()
        await ctx.message.channel.send(file=discord.File(img, "chart.png"))