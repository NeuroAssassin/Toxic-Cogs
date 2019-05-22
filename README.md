# Toxic-Cogs
[![Discord server](https://discordapp.com/api/guilds/540613833237069836/embed.png)](https://discord.gg/vQZTdB9)
[![Black coding style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)
[![Red cogs](https://img.shields.io/badge/Red--DiscordBot-cogs-red.svg)](https://github.com/Cog-Creators/Red-DiscordBot/tree/V3/develop)
[![discord.py](https://img.shields.io/badge/discord-py-blue.svg)](https://github.com/Rapptz/discord.py)

Cogs for Red - Discord Bot by TwentySix.
****
## Table of Contents
* [Information](#information)
* [How to Install](#how-to-install)
* [Descriptions](#descriptions)
* [Credits](#credits)
* [Bugs and Help](#bugs-and-help)
* [Helpful Libraries](#helpful-libraries)
* [Required Libraries](#required-libraries)
****
### Information

The Toxic-Cogs repo holds a bunch of different cogs, some being tools (listpermissions, maintenance), some being for fun (like simon, twenty (2048)) and some others giving information (sw (Star Wars)).  You can find descriptions of them below in the table.

[Back to Table of Contents](#table-of-contents)
****
### How to install

These cogs are made for [Red V3](https://github.com/Cog-Creators/Red-DiscordBot) by TwentySix.  Using Red V3, you can add my repo by doing `[p]repo add Toxic-Cogs https://github.com/NeuroAssassin/Toxic-Cogs master`, then using `[p]cog install Toxic-Cogs <cog-name>` (with `[p]` being your prefix)

[Back to Table of Contents](#table-of-contents)
****
### Descriptions

| Cog | Description |
| --- | ----------- |
| Color | <details><summary>Get information about colors</summary>Provide either the name, rgb, hexadecimal or hsl value of a color and get the rgb, hexadecimal and hsl value about it</details> |
| Commandchart | <details><summary>Get the latest commands</summary>Get the latest commands from the last certain amount of messages in a certain channel</details> |
| Cooldown | <details><summary>Set cooldowns for commands</summary>Override (not recommended) or set cooldowns for commands to make sure your users don't commands too much </details> |
| ListPermissions | <details><summary>List the permissions of a role or user</summary>Get the permissions of a user or role in a certain channel or guild-wide.</details> |
| Minesweeper | <details><summary>Play minesweeper in Discord</summary>Play minesweeper interactively on the bot or with spoilers</details> |
| Simon | <details><summary>Play Simon in Discord</summary>Play Simon in Discord and guess the correct sequences</details> |
| SQL | <details><summary>Store data in Discord with SQL</summary>Store data in a database inside of Discord to call for later use, and limit those who can access or edit the data</details> |
| Twenty | <details><summary>Play 2048 in Discord</summary>Play 2048 in Discord with reactions</details> |
| UpdateChecker | <details><summary>Get notifications when there is an update for one of your repositories added to your bot</summary>Have your bot tell you in DM or a channel when there is an update for one of the repos added to your bot</details> |
| SW | <details><summary>Get Star Wars information through Discord</summary>Get info about something in Star Wars using this cog</details> |
| Maintenance | <details><summary>Put your bot on maintenance</summary>Put your bot on maintenance, telling people who are not in the whitelist for the maintenance that the bot is on maintenance, and will not respond to commands</details> |
| Evolution | <details><summary>Buy animals with economy credits and get more credits!</summary>A cog that I made after a mobile app, kinda cheesy but fun.</details> |
| Switcher | <details><summary>Switch between bot accounts quick and easily</summary>Register the bot with a name and the correct token, then just run a command to easily switch to it</details> |
| Deleter | <details><summary>Auto-delete messages after a certain amount of time</summary>Delete messages after a certain amount of specified time, after the message was sent</details> |
| Editor | <details><summary>Edit messages sent by the bot</summary>Allows an administrator to edit one of the bot's messages, by either copying the content and/or embed from a previously sent message from the bot, or by the specified content</details> |
| Targeter | <details><summary>Target users in the guild based upon the passed arguments</summary>Allows arguments for dates, roles, names, activities, statuses or devices.</details> |

[Back to Table of Contents](#table-of-contents)
****
### Credits

Credit to Aikaterna's chatchart cog, which I based my commandchart cog off of (which was also a requested cog on cogboard.red).  You can find that cog here: https://github.com/aikaterna/aikaterna-cogs/tree/v3/chatchart.

Thanks to:
+ Yukirin for suggesting/asking for the commandchart cog.
+ Olaroll for suggesting/asking for the editor cog
+ kennnyshiwa for suggestin/asking for the deleter cog
+ Other people in Red for helping me with coming up with ideas and helping me find shortcuts to some things

[Back to Table of Contents](#table-of-contents)
****
### Bugs and Help
For bugs, contact me at Neuro Assassin#4779 <@473541068378341376>.  It would be best though to join my support server, where other people could help you too.  You can find the invite button at the top of this file.

[Back to Table of Contents](#table-of-contents)
****
### Helpful Libraries
[PrettyTable](https://pypi.org/project/PrettyTable/) is helpful for the SQL cog.  It makes the showing of the data much nicer, neater and more comprehendible.

[Back to Table of Contents](#table-of-contents)
****
### Required Libraries
[Matplotlib](https://pypi.org/project/matplotlib/) and [pytz](https://pypi.org/project/pytz/) are required for the commandchart cog.

[Colour](https://pypi.org/project/colour/) is required for the color cog.

[PrettyTable](https://pypi.org/project/PrettyTable/) and [FuzzyWuzzy](https://pypi.org/project/fuzzywuzzy/) are required for the listpermissions cog.

[Back to Table of Contents](#table-of-contents)