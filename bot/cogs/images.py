"""This is a cog for a discord.py bot.
It will save an attached image to disk

Commands:
    save       save image to disk
    send       send attached image to api

Only users which are specified as a superuser in the config.json
can run commands from this cog.
"""

import time
from os.path import splitext
import os
from typing import Iterable
import aiofiles
from pathlib import Path
from bot import Levi
from inspect import Parameter
from discord.errors import HTTPException
from discord.ext import commands
from discord.ext.commands.bot import Bot
from discord.message import Attachment
from discord.ext.commands.context import Context
from urllib.parse import urlparse


class Images(commands.Cog, name="Image"):
    def __init__(self, client: Levi):
        self.client = client

    async def cog_check(self, ctx: Context):
        return self.client.user_is_admin(ctx.author)

    def get_ext(self, url: str):
        """Return the filename extension from url, or ''"""
        parsed = urlparse(url)
        root, ext = splitext(parsed.path)
        return ext  # or ext[1:] if you don't want the leading '.'

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
            file = Path(
                f'../downloaded/{time.strftime("%Y-%m-%d-%H-%M-%S")}_{i}{self.get_ext(url)}'
            )
            async with self.client.session.get(url) as r:
                if r.status == 200:
                    async with aiofiles.open(
                        file,
                        mode="wb",
                    ) as f:
                        await f.write(await r.read())
                else:
                    self.client.log_error(HTTPException(r, "File Download Error"), ctx)
            await ctx.send(f"File `{file.name}` saved")
            print(str(file), "received")

    @commands.command(name="send", description="Send attached image to Server")
    async def send(self, ctx: Context, *, message: str):
        """Send an attached image (and text) to my API"""

        api_endpoint = "http://localhost:80/api/v1/send_image"
        for url in self.get_attachment_urls(ctx):
            body = {"url": url, "text": message}
            async with self.client.session.post(api_endpoint, json=body) as r:
                print(await r.json())
        print(body)

    @commands.command(name="ls")
    async def ls(self, ctx: Context):
        files = os.listdir("../images/")
        response = ["\n-- images/\n"]
        response += ["  - " + file + "\n" for file in files]
        await ctx.send(f'```css{"".join(response)}```')


def setup(client):
    client.add_cog(Images(client))
