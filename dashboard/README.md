# Dashboard README
Hey there, thanks for looking at my dashboard!  This cog allows for you (the owner) to control your bot through a web dashboard, easily.  This can also be used for other people using the dashboard as well, as the dashboard uses Discord OAuth to log you in, and to make sure it respects permissions.

## Setup
### Inital installation
First, if you haven't already, add my repo:
> `[p]repo add toxic https://github.com/NeuroAssassin/Toxic-Cogs`

Next, install the cog:
> `[p]cog install toxic dashboard`

Finally, load the cog:
> `[p]load dashboard`
****
> NOTE: In order for the dashboard to make connection to the bot, you MUST start the bot with the `--rpc` flag.
****
### Setup web server
> NOTE: If you are using the cog for more than one bot, then you will have to change the ports to another, including the webserver port (which is attached to the redirect URI) and the RPC port (which you can change with the `--rpc-port` flag, followed by the port number, like this: `--rpc-port 5000`)
#### Bot
##### Redirect URI
Head over [here](https://discordapp.com/developers/applications/) to the Discord Developer Console, and click on your bot's application.  Note that it **must be** the bot you are setting this up for.  Next, click on the OAuth2 tab and click "Add Redirect".  Then, put the appropriate link down based upon what you are planning to do and how you are hosting:
> NOTE: If you are running multiple bots with this cog, you will need to change the port below to the port you use when using the `--port` flag with the webserver.
****
###### If you are hosting on a VPS:
- http://ip.add.re.ss:42356/callback (make sure to replace "ip.add.re.ss" with your VPS's IP address).
###### If you are hosting on a local computer:
- http://localhost:42356/callback (if you aren't planning on allowing other people to use it)
- http://loc.al.ip.address:42356/callback (also if you aren't planning on other people using it, but note that you must replace "loc.al.ip.address" with the one found in `ipconfig` in the command prompt, under IPv4).
- http://ip.add.re.ss:42356/callback (if you are planning on making it public.  Note that this requires port forwarding set up, and the "ip.add.re.ss" must be replaced with the IP you see when you look up "what is my ip address").
****
Next, copy the redirect URI you just put into the field, and head over to the dashboard.  Type the following, replacing `<redirect>` with your redirect.
> `[p]dashboard settings oauth redirect <redirect>`
##### Client Secret
Head over [here](https://discordapp.com/developers/applications/) to the Discord Developer Console, and click on your bot's application.  Just like with the Redirect URI, this must be the same bot.  Next, head over to the right of the page and click on "Copy" under the Client Secret, NOT the Client ID.  Finally, head over to Discord and type the following command, replacing `<secret>` with your client secret:
> `[p]dashboard settings oauth secret <secret>`

Wew, now the bot's side is finished!  Let's go configure and start the webserver
#### Webserver
Now, navigate to `<install_path>\dashboard\data` (you can find your install path by running `[p]paths`).  To start the webserver, you need to run `python run.py --instance <instancename>`.  Note that `instancename` must be the name you start the bot with, when you run `redbot <instancename>`.  If you have multiple bots running at the same time with the cog, you need to configure a few things.  First, change the port the webserver is running on (default 42356).  You can do this by adding to the `python` command `--port <port>`.  Next, change the RPC port that is being used.  This will be the port you set when starting the bot with the `--rpc-port` flag.  Use the same syntax and add that to the `python` command like this: `--rpc-port <port>`.  In conclusion, if I was starting the webserver, to run on port 5000, and I had started my bot with `redbot jarvis --rpc-port 45612`, I would start the webserver with this command:

> `python run.py --instance jarvis --port 5000 --rpc-port 45612`.

There you go!  Your dashboard should be up and running.  If you have any questions, feel free to contact me in the Cog Support server, or in my personal server, listed below.
****
## Configuration and Other Details
### Permissions
In order to make sure all permissions are respected, Discord OAuth is used for authentication for the dashboard.  This helps make sure that random users don't end up using the `[p]serverlock` command in the dashboard.  Permissions are judged based upon whether they are bot owner, guild owner, administrator, moderator or a normal user (in that order).  If not, the respective button will be greyed out, or they will receive a popup saying they aren't allowed to perform that operation.
### Contact
If you have any questions, issues or suggestions, feel free to stop by my server and tell me about them:
[![Discord server](https://discordapp.com/api/guilds/540613833237069836/embed.png?style=banner3)](https://discord.gg/vQZTdB9)