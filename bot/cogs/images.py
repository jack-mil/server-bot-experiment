"""This is a cog for a discord.py bot.
It will save an attached image to disk

Commands:
    save       save image to disk
    send       send attached image to api

Only users which are specified as a superuser in the config.json
can run commands from this cog.
"""

import os
import time
from inspect import Parameter
from os.path import splitext
from pathlib import Path, PurePath
from typing import Generator, Iterable
from urllib.parse import urlparse

import aiofiles
from bot import Levi
from discord import client
from discord.channel import DMChannel
from discord.errors import HTTPException
from discord.ext import commands
from discord.ext.commands.context import Context
from discord.message import Attachment, Message


class Images(commands.Cog, name="Image"):
    def __init__(self, client: Levi):
        self.client = client

    async def cog_check(self, ctx: Context):
        return self.client.user_is_admin(ctx.author)

    def get_attachment_urls(self, ctx: Context) -> Iterable[str]:
        if len(images := ctx.message.attachments) == 0:
            raise commands.MissingRequiredArgument(
                Parameter("attached_file", Parameter.POSITIONAL_ONLY, type=Attachment)
            )
        return (image.url for image in images)

    @commands.command(name="save", description="Save an attachment to disk")
    async def save(self, ctx: Context):
        """Save an attachment"""
        await ctx.trigger_typing()
        for i, url in enumerate(self.get_attachment_urls(ctx)):
            output_file = Path(
                self.client.config.get("save_dir"),
                time.strftime("%Y-%m-%d-%H-%M-%S")
                + (f"_{i}" if i > 0 else "")
                + PurePath(url).suffix,
            )
            output_file.parent.mkdir(parents=True, exist_ok=True)
            async with self.client.session.get(url) as r:
                if r.status == 200:
                    async with aiofiles.open(
                        output_file,
                        mode="wb",
                    ) as f:
                        await f.write(await r.read())
                else:
                    self.client.log_error(HTTPException(r, "File Download Error"), ctx)
            await ctx.send(f"File `{output_file.name}` saved")
            print(str(output_file), "received")

    @commands.command(name="send", description="Send attached image to Server")
    async def send(self, ctx: Context, *, message: str = None):
        """Send an attached image (and text) to my API"""
        config = self.client.config
        api_endpoint = config["api_root"] + config["api_send_endpoint"]

        for url in self.get_attachment_urls(ctx):
            body = {"url": url, "text": message}
            async with self.client.session.post(api_endpoint, json=body) as r:
                print(await r.json())

    @commands.command(name="ls")
    async def ls(self, ctx: Context):
        files = Path(self.client.config.get("save_dir")).iterdir()
        response = ["\n-- images/\n"]
        response += [f"  - {file}\n" for file in files]
        await ctx.send(f'```css{"".join(response)}```')


def setup(client: Levi):
    client.add_cog(Images(client))

    @client.event
    async def on_message_edit(before: Message, after: Message):
        if isinstance(after.channel, DMChannel):
            await client.process_commands(after)
