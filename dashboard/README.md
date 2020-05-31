# Red Dashboard - Bot Client
*An easy-to-use interactive web dashboard to control your Redbot.*

## Installation
First, if you haven't already, add my repo:
> `[p]repo add toxic https://github.com/NeuroAssassin/Toxic-Cogs`

Next, install the cog:
> `[p]cog install toxic dashboard`

Finally, load the cog:
> `[p]load dashboard`

> NOTE: In order for the dashboard to make connection to the bot, you MUST start the bot with the `--rpc` flag.

## Configuration
### Dashboard with one bot
1. Obtain your bot's client secret and run the command (in Discord) `[p]dashboard settings oauth secret <secret>`, replacing `<secret>` with the secret.  You can get your secret by following these steps:
    1. Log into the Discord Developer Console (found [here](https://discord.com/developers/applications)), and click on your bot's application
    2. Under your application's name, on the right, it should say "Client Secret" (NOT "Client ID"), and have a Copy button under it.
    3. Click the Copy button, and paste that into the command above.
    4. Keep the developer console page open for a later step.
2. Set the OAuth2 redirect with `[p]dashboard settings oauth redirect <redirect>`, replacing `<redirect>`
    1. If you are on the same device as the webserver, you can make the redirect `http://127.0.0.1:42356/callback`.
    2. If you are on a difference device as the webserver, you can set the redirect to `http://ip.add.re.ss:42356/callback`, replacing `ip.add.re.ss` with the webserver device's public IP address (your host should tell you it).  NOT RECOMMENDED DUE TO SECURITY REASONS.
    3. If you are hosting on a domain, set the redirect url to `<domain>/callback`, replacing `<domain>` with your domain.
3. Take the redirect you set with step 2, copy it to your clipboard so that they are EXACTLY the same.  Then, head back to the Discord Developer Console, click on the Oauth2 tab and paste the redirect in one of the redirect text boxes.
4. (Optional) Grab an invite for your support server and paste it into the command `[p]dashboard settings support <url>`, replacing `<url>` with the invite.

The cog is now fully configured.  If you haven't already, follow the instructions [here](https://github.com/NeuroAssassin/Red-Dashboard) to setup the webserver for the dashboard.

### Dashboard with multiple bots
Having multiple bots running dashboard is a bit more tricky.  Follow the instructions exactly:

1. Make a list of two ports for each bot that will be running dashboard.  Ports must be between the number 1 and 65535.  One port will be for rpc (from now on known as `<rpcport>`) and one for the webserver (from now on known as `<webport>`).  If you have already created a list of ports when following the instructions when setting up the webserver, you MUST USE THOSE INSTEAD.
> When creating the ports, it is highly recommended to use ports that are a higher number, as lower ports are usually used by other applications.
2. Stop each bot, and then restart them with the additional flags: `--rpc --rpc-port <rpcport>`, replacing `<rpcport>` with the RPC Port you designated for that bot.
3. Follow step 1 of the one bot instructions, and repeat for each bot you are setting the dashboard up with.
4. Follow steps 2-4 of the one bot instructions, HOWEVER replace the number `42356` wherever you see it with the `<webport>` you specified in the list you made earlier, for each of your bots that you are setting up.

Once you have finished those instructions with all of your bots, the cogs should be fully configured on each of them.  Next, follow the instructions [here](https://github.com/NeuroAssassin/Red-Dashboard) to setup the webserver for each bot, and make sure to follow the instructions for the multiple bots and to use the list of ports you crated above.

## Contact/Issues
If you have any questions, issues or suggestions, feel free to stop by my server and tell me about them:
[![Discord server](https://discordapp.com/api/guilds/540613833237069836/embed.png?style=banner3)](https://discord.gg/vQZTdB9)