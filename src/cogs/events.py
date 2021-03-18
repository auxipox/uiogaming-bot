from discord.ext import commands, tasks
import discord

import gspread
from datetime import datetime
from aio_timers import Timer


class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.event_scheduler.start()
        self.scheduled_dates = []
        self.scheduled_events = []

    @commands.command()
    async def arrangementer(self, ctx):
        event_string = ''
        for event in self.scheduled_events:
            event_string += f'{event["date"]} - {event["title"]}\n'

        embed = discord.Embed(color = ctx.me.color, title='Arrangementer i sendingsliste', description=event_string)
        await ctx.send(embed=embed)

    @tasks.loop(hours=1.0)
    async def event_scheduler(self, reconnect = True):
        print('FETCHING EVENTS')

        gc = gspread.service_account(filename='./src/config/google-credentials.json')
        sheet = gc.open_by_key(self.bot.event_scheduler['sheet_id'])
        worksheet = sheet.get_worksheet(0)
        data = worksheet.get_all_values()

        for column in data:
            if column[0] == 'Dato':
                continue

            column[0] = column[0].replace('kl. ', '')  # for some reason, strip() doesn't work
            try:
                date = datetime.strptime(column[0], '%d.%m.%Y %H.%M.%S')
            except ValueError:
                continue

            if date < datetime.now() or date in self.scheduled_dates:
                continue

            title = column[1]
            description = column[2]
            roles = column[3].split(',')
            index = len(self.scheduled_events)

            print('Adding to schedule', title, date)

            run_in = (date - datetime.now()).total_seconds()

            args = (title, description, roles, index)
            Timer(run_in, self.event_sender, args)
            self.scheduled_dates.append(date)
            self.scheduled_events.append(
                {
                    'index': len(self.scheduled_events),
                    'date': date,
                    'title': title,
                }
            )

    async def event_sender(self, title, description, roles, index):
        print('SENDING EVENT', title)

        guild = self.bot.get_guild(self.bot.event_scheduler['guild_id'])
        channel = self.bot.get_channel(self.bot.event_scheduler['channel_id'])

        mentions = ''
        for role in roles:
            try:
                role = guild.get_role(int(role))
            except ValueError:
                break
            mentions += f'{role.mention} '
        embed = discord.Embed(color=discord.Color.red(), title=title, description=description)
        embed = await channel.send(mentions, embed=embed)

        self.scheduled_events = [i for i in self.scheduled_events if i['index'] != index]

    def cog_unload(self):
        self.event_scheduler.cancel()

    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True)
    @commands.group()
    async def loop(self, ctx):
        """Manipulér loop"""

        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @loop.command()
    async def start(self, ctx):
        """Starter loop"""

        self.event_scheduler.start()
        await ctx.send(':thumbsup:')

    @loop.command(aliases=['restart'])
    async def omstart(self, ctx):
        """Starter loop på nytt"""

        self.event_scheduler.restart()
        await ctx.send(':thumbsup:')

    @loop.command(aliases=['stop'])
    async def stopp(self, ctx):
        """Stopper loop (foregående loop)"""

        self.event_scheduler.stop()
        await ctx.send(':thumbsup:')

    @loop.command(aliases=['cancel'])
    async def avbryt(self, ctx):
        """Stopper loop (og fremtidige)"""

        self.event_scheduler.cancel()
        await ctx.send(':thumbsup:')

    @event_scheduler.before_loop
    async def before_upate_roles(self):
        """Delays loop initialization until the bot is ready for use"""

        await self.bot.wait_until_ready()

    @event_scheduler.after_loop
    async def on_event_scheduler_cancel(self):
        """Prints cancel message when loop is cancelled"""

        if self.event_scheduler.is_being_cancelled():
            print('Stopper loop...')


def setup(bot):
    bot.add_cog(Events(bot))
