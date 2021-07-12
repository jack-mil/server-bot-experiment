"""This is a cog for a discord.py bot.
It will add some management commands to a bot.

Commands:
    load            load an extension / cog
    unload          unload an extension / cog
    reload          reload an extension / cog
    cogs            show currently active extensions / cogs
    version         show the hash of the latest commit
    pull            pull latest changes from github (superuser only)
"""
import json
from bot import Levi
import re
import subprocess
import typing
from datetime import datetime
from os import listdir, path

from discord import Activity, File
from discord.ext import commands


class Management(commands.Cog, name='Management'):
    def __init__(self, client: Levi):
        self.client = client
        self.reload_config()
        self.cog_re = re.compile(r'\s*src\/cogs\/(.+)\.py\s*\|\s*\d+\s*[+-]+')

    async def cog_check(self, ctx):
        return self.client.user_is_admin(ctx.author)

    def get_version_info(self):
        version = 'unknown'
        date = 'unknown'
        try:
            gitlog = subprocess.check_output(
                ['git', 'log', '-n', '1', '--date=iso']
            ).decode()
            for line in gitlog.split('\n'):
                if line.startswith('commit'):
                    version = line.split(' ')[1]
                elif line.startswith('Date'):
                    date = line[5:].strip()
                    date = date.replace(' +', '+').replace(' ', 'T')
                else:
                    pass
        except Exception as e:
            self.client.last_errors.append((e, datetime.utcnow(), None))
            raise e
        return (version, date)

    async def get_remote_commits(self):
        last_commit = self.get_version_info()[0]
        ext = f'?per_page=10&sha=master'
        repo = self.client.config['github_repo']
        auth_key = self.client.config.get('github_key')
        header = None
        if auth_key:
            header = {'Authorization': f'token {auth_key}'}
        nxt = f'https://api.github.com/repos/{repo}/commits{ext}'
        repo_data = []
        repo_shas = []
        while last_commit not in repo_shas:
            async with self.client.session.get(nxt, headers=header) as response:
                r = await response.json()
            repo_data += r
            repo_shas = [x['sha'] for x in repo_data]
            try:
                nxt = r.links['next']['url']
            except:
                nxt = ''
        num_comm = repo_shas.index(last_commit)
        return (num_comm, repo_data[0 : (num_comm if num_comm > 10 else 10)])

    def reload_config(self):
        with open("config.json") as conffile:
            self.client.config = json.load(conffile)

    def crawl_cogs(self, directory='cogs'):
        cogs = []
        for element in listdir(directory):
            if element in ('samples', 'utils'):
                continue
            abs_el = path.join(directory, element)
            if path.isdir(abs_el):
                cogs += self.crawl_cogs(abs_el)
            else:
                filename, ext = path.splitext(element)
                if ext == '.py':
                    dot_dir = directory.replace('\\', '.')
                    dot_dir = dot_dir.replace('/', '.')
                    cogs.append(f'{dot_dir}.' + filename)
        return cogs

    @commands.Cog.listener()
    async def on_ready(self):
        loaded = self.client.extensions
        unloaded = [x for x in self.crawl_cogs() if x not in loaded]
        # Cogs without extra in their name should be loaded at startup so if
        # any cog without "extra" in it's name is unloaded here -> Error in cog
        errors = [cog_name for cog_name in unloaded if 'extra' not in cog_name]
        if errors:
            activity_name = f'ERROR in cogs {errors}'
            activity_type = 3
        else:
            bot_version = self.get_version_info()[0][:7]
            activity_name = f'on {bot_version}'
            activity_type = 0
        await self.client.change_presence(
            activity=Activity(name=activity_name, type=activity_type)
        )

    # ----------------------------------------------
    # Function to disply the version
    # ----------------------------------------------
    @commands.command(
        name='version',
        brief='Show current version of the bot',
        description='Show current version and changelog of the bot',
        hidden=True,
    )
    async def version(self, ctx):
        await ctx.trigger_typing()
        version, date = self.get_version_info()
        num_commits, remote_data = await self.get_remote_commits()
        status = "I am up to date with 'origin/master'"
        changelog = 'Changelog:\n'
        if num_commits:
            status = (
                f"I am [{num_commits}] commits behind 'origin/master'"
                f" [{remote_data[0]['commit']['author']['date']}]"
            )
        for i, commit in enumerate(remote_data):
            commitmessage = commit['commit']['message']
            if 'merge pull' in commitmessage.lower():
                continue
            changelog += (
                ('+ ' if i < num_commits else '* ')
                + commitmessage.split('\n')[0]
                + '\n'
            )
        await ctx.send(
            f'```css\nCurrent Version: [{version[:7]}].from [{date}]'
            + f'\n{status}``````diff\n{changelog}```'
        )

    # ----------------------------------------------
    # Function to load extensions
    # ----------------------------------------------
    @commands.command(
        name='load',
        brief='Load bot extension',
        description='Load bot extension',
        hidden=True,
    )
    async def load_extension(self, ctx, extension_name):
        for cog_name in self.crawl_cogs():
            if extension_name in cog_name:
                target_extension = cog_name
                break
        try:
            self.client.load_extension(target_extension)
        except Exception as e:
            await self.client.log_error(e, ctx)
            await ctx.send(f'```py\n{type(e).__name__}: {str(e)}\n```')
            return
        await ctx.send(f'```css\nExtension [{target_extension}] loaded.```')

    # ----------------------------------------------
    # Function to unload extensions
    # ----------------------------------------------
    @commands.command(
        name='unload',
        brief='Unload bot extension',
        description='Unload bot extension',
        hidden=True,
    )
    async def unload_extension(self, ctx, extension_name):
        for cog_name in self.client.extensions:
            if extension_name in cog_name:
                target_extension = cog_name
                break
        if target_extension.lower() in 'cogs.management':
            await ctx.send(
                f"```diff\n- {target_extension} can't be unloaded"
                + f"\n+ try reload instead```"
            )
            return
        if self.client.extensions.get(target_extension) is None:
            return
        self.client.unload_extension(target_extension)
        await ctx.send(f'```css\nExtension [{target_extension}] unloaded.```')

    # ----------------------------------------------
    # Function to reload extensions
    # ----------------------------------------------
    @commands.command(
        name='reload',
        brief='Reload bot extension',
        description='Reload bot extension',
        hidden=True,
        aliases=['re'],
    )
    async def reload_extension(self, ctx, extension_name):
        target_extensions = []
        if extension_name == 'all':
            target_extensions = [__name__] + [
                x for x in self.client.extensions if not x == __name__
            ]
        else:
            for cog_name in self.client.extensions:
                if extension_name in cog_name:
                    target_extensions = [cog_name]
                    break
        if not target_extensions:
            return
        result = []
        for ext in target_extensions:
            try:
                self.client.reload_extension(ext)
                result.append(f'Extension [{ext}] reloaded.')
            except Exception as e:
                await self.client.log_error(e, ctx)
                result.append(f'#ERROR loading [{ext}]')
                continue
        result = '\n'.join(result)
        await ctx.send(f'```css\n{result}```')

    # ----------------------------------------------
    # Function to get bot extensions
    # ----------------------------------------------
    @commands.command(
        name='cogs',
        brief='Get loaded cogs',
        description='Get loaded cogs',
        aliases=['extensions'],
        hidden=True,
    )
    async def print_cogs(self, ctx):
        loaded = self.client.extensions
        unloaded = [x for x in self.crawl_cogs() if x not in loaded]
        response = ['\n[Loaded extensions]'] + ['\n  ' + x for x in loaded]
        response += ['\n[Unloaded extensions]'] + ['\n  ' + x for x in unloaded]
        await ctx.send(f'```css{"".join(response)}```')
        return True

    # ----------------------------------------------
    # Command to pull the latest changes from github
    # ----------------------------------------------
    @commands.group(
        name='git',
        hidden=True,
    )
    async def git(self, ctx):
        """Commands to run git commands on the local repo"""
        pass

    @git.command(
        name='pull',
    )
    async def pull(self, ctx, noreload: typing.Optional[str] = None):
        """Pull the latest changes from github"""
        await ctx.trigger_typing()
        try:
            output = subprocess.check_output(['git', 'pull']).decode()
            await ctx.send('```git\n' + output + '\n```')
        except Exception as e:
            return await ctx.send(str(e))

        if noreload is not None:
            return

        _cogs = [f'cogs.{i}' for i in self.cog_re.findall(output)]
        active_cogs = [i for i in _cogs if i in self.client.extensions]
        if active_cogs:
            for cog_name in active_cogs:
                await ctx.invoke(self.client.get_command('reload'), cog_name)

    # ----------------------------------------------
    # Command to reset the repo to a previous commit
    # ----------------------------------------------
    @git.command(
        name='reset',
    )
    async def reset(self, ctx, n: int):
        """Reset repo to HEAD~[n]"""
        if not n > 0:
            raise commands.BadArgument('Please specify n>0')
        await ctx.trigger_typing()
        try:
            output = subprocess.check_output(
                ['git', 'reset', '--hard', f'HEAD~{n}']
            ).decode()
            await ctx.send('```git\n' + output + '\n```')
        except Exception as e:
            await ctx.send(str(e))

    # ----------------------------------------------
    # Command to stop the bot
    # ----------------------------------------------
    @commands.command(name='restart', aliases=['shutdown'], hidden=True)
    async def shutdown(self, ctx):
        """Stop/Restart the bot"""
        await self.client.close()

    # ----------------------------------------------
    # Command to toggle maintenance mode
    # ----------------------------------------------
    @commands.command(name='maintenance', hidden=True)
    async def maintenance(self, ctx):
        """Toggle maintenance mode"""
        if self.client.maintenance_mode:
            self.client.maintenance_mode = False
            await self.client.change_presence(activity=self.client.default_activity)
        else:
            self.client.maintenance_mode = True
            await self.client.change_presence(activity=self.client.maintenance_activity)


def setup(client):
    client.add_cog(Management(client))
