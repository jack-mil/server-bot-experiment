"""Basic Discord Bot

This file starts the bot and loads all extensions/cogs and configs/permissions
The Bot automatically tries to load all extensions found in the "cogs/" folder
plus the hangman.hangman extension.

An extension can be reloaded without restarting the bot.
The extension "management" provides the commands to load/unload other extensions

This bot requires discord.py
    pip install -U discord.py
"""
import json
import logging
import os
import sys
import traceback
from datetime import datetime
from logging import handlers
from os import listdir, path

import discord
from aiohttp import ClientSession, ClientTimeout
from discord import AllowedMentions, DMChannel, User
from discord.ext.commands import Bot, Context, when_mentioned_or


class Levi(Bot):
    def __init__(self, *args, **options):
        super().__init__(*args, **options)
        self.session: ClientSession = None
        with open('config.json') as conffile:
            self.config = json.load(conffile)
        self.last_errors = []

    async def start(self, *args, **kwargs):
        self.session = ClientSession(timeout=ClientTimeout(total=30))
        await super().start(self.config["bot_key"], *args, **kwargs)

    async def close(self):
        await self.session.close()
        await super().close()

    def user_is_admin(self, user):
        return user.id in self.config['admins']

    def user_is_superuser(self, user: User):
        return user.id in self.config['superusers']

    async def log_error(self, error: Exception, error_source: Context = None):
        is_context = isinstance(error_source, Context)
        has_attachment = bool(error_source.message.attachments) if is_context else False
        self.last_errors.append(
            (
                error,
                datetime.now(),
                error_source,
                error_source.message.content if is_context else None,
                error_source.message.attachments[0] if has_attachment else None,
            )
        )


client = Levi(
    command_prefix=when_mentioned_or(''),
    description='Send n00ds',
    max_messages=15000,
    intents=discord.Intents(dm_messages=True),
    allowed_mentions=AllowedMentions.none(),
)

STARTUP_EXTENSIONS = []

for file in listdir(path.join(path.dirname(__file__), 'cogs/')):
    filename, ext = path.splitext(file)
    if '.py' in ext:
        STARTUP_EXTENSIONS.append(f'cogs.{filename}')

for extension in reversed(STARTUP_EXTENSIONS):
    try:
        client.load_extension(f'{extension}')
    except Exception as e:
        client.last_errors.append((e, datetime.utcnow(), None, None))
        exc = f'{type(e).__name__}: {e}'
        print(f'Failed to load extension {extension}\n{exc}')


@client.event
async def on_ready():
    print('\nActive in these guilds/servers:')
    [print(g.name) for g in client.guilds]
    print('\nImage Bot started successfully')
    return True


@client.event
async def on_error(event_method, *args, **kwargs):
    """|coro|

    The default error handler provided by the client.

    By default this prints to :data:`sys.stderr` however it could be
    overridden to have a different implementation.
    Check :func:`~discord.on_error` for more details.
    """
    print(
        'Default Handler: Ignoring exception in {}'.format(event_method),
        file=sys.stderr,
    )
    traceback.print_exc()
    # --------------- custom code below -------------------------------
    await client.log_error(sys.exc_info()[1], 'DEFAULT HANDLER:' + event_method)


@client.event
async def on_message(msg):
    if isinstance(msg.channel, DMChannel):
        await client.process_commands(msg)


# Setup logging
log_filename = '../logs/discord.log'
os.makedirs(os.path.dirname(log_filename), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        handlers.RotatingFileHandler(
            filename=log_filename,
            encoding='utf-8',
            maxBytes=(1048576 * 5),
            backupCount=7,
        ),
    ],
)
logging.info('STARTING BOT NOW')

# Start the bot (blocking call)
client.run()
print('Image Bot has exited')
