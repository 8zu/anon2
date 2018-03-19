import logging
import os.path as osp
import sys
from collections import namedtuple
import random

import pytoml

from persistent import Cache

try:
    from discord.ext import commands
    from discord import utils
    import discord
except ImportError:
    print("Discord.py is not installed.\n"
          "Consult the guide for your operating system "
          "and do ALL the steps in order.\n"
          "https://twentysix26.github.io/Red-Docs/\n")
    sys.exit(1)

config_path = './config.toml'
description = """A simple bot to post anonymously"""

logging.basicConfig(filename='discord.log', level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s')
logger = logging.getLogger('anonbot2')

def get_config(path):
    if osp.exists(path):
        return pytoml.load(open(path, "r", encoding="UTF-8"))
    else:
        logger.error("Missing config file! Shutting down now...")
        sys.exit(1)

class NotJoinedServerException(Exception):
    pass
class NotSubscribedToChannelException(Exception):
    pass

class MissingPermissionError(Exception):
    def __init__(self, cause):
        self.cause = cause

Command = namedtuple('Command', ['command', 'argv'])

class AnonBot(commands.Bot):
    rule = '__' + (' ' * 150) + '__'

    def __init__(self, cache, texts):
        super().__init__(description=description, command_prefix=':a')
        self.cache = cache
        self.texts = texts
        self.initialized = False
        self.header = texts['header']
        self.counter = 0
        self.anon_role = None

    def is_me(self, author):
        return author == self.user

    def is_owner(self, author):
        return self.server and author == self.server.owner

    def is_eligible(self, author):
        return True

    def is_command(self, cmd, s):
        return s.strip().split(' ')[0] == f"{self.command_prefix}{cmd}"

    def like_command(self, cmd, s):
        return s.strip().split(' ')[0].startswith(f"{self.command_prefix}{cmd}")

    def find_channel(self, name):
        return utils.find(lambda ch: ch.name == name, self.get_all_channels())

    def resume(self, config):
        if self.initialized:
            return

        self.server = self.cache.load('server.json').get_or(None)
        if not self.server:
            logger.info("The bot has not joined a server, initialization incomplete")
            raise NotJoinedServerException()
        self.server = self.get_server(self.server)
        if not self.server:
            logger.error("The bot joined a server but was kicked out.")
            self.cache.purge('server.json')
            raise NotJoinedServerException()
        self.member = self.server.get_member(self.user.id)

        perm = self.member.server_permissions
        if not perm.send_messages:
            raise MissingPermissionError("send message")
        if not perm.manage_messages:
            raise MissingPermissionError("manage messages")

        self.main_channel = self.cache.load('main-channel.json') \
                                      .then(self.server.get_channel)
        if self.main_channel.is_none():
            logger.error('The bot has not been subscribed to a channel. Initialization incomplete')
            raise NotSubscribedToChannelException()
        self.main_channel = self.main_channel.get()
        if not self.main_channel:
            logger.error('The main channel has been deleted')
            self.cache.purge('main-channel.json')
            raise NotSubscribedToChannelException()

        logger.info("Initialization complete")
        self.initialized = True
        self.counter = 0
        return

    async def cleanup_after(self, reply, member):
        await self.delete_messages([reply, *self.vetting_room[member.id]])

    def decorated_header(self):
        return '\n'.join(['```css', self.header.format(counter=f'{self.counter:04}', id=random.randint(10000, 99999)), '```'])

    async def forward(self, msg):
        self.counter += 1
        frame = '\n'.join([self.decorated_header(), msg.content])
        await self.send_message(self.main_channel, frame)

    async def erase_and_repost(self, msg):
        await self.forward(msg)
        await self.delete_message(msg)

    @staticmethod
    def record_message(msg):
        logger.info(f"Receive message from {msg.author.name}@{msg.author.id}: {msg.content}")

    @staticmethod
    def record_dm(dm):
        logger.info(f"Receive DM from {dm.author.name}@{dm.author.id}: {dm.content}")


def initialize(config):
    cache = Cache(config['cache_root'])
    texts = get_config(config['text_path'])
    bot = AnonBot(cache, texts)

    @bot.event
    async def on_ready():
        try:
            bot.resume(config)
        except MissingPermissionError as ex:
            logger.error(f"I don't have the required permission to {ex.cause}. Please fix")
        except NotJoinedServerException:
            return
        except NotSubscribedToChannelException:
            return

        if bot.initialized:
            print(f'Server: {bot.server.name}')
            print(f'Bot channel: #{bot.main_channel.name}')

    @bot.event
    async def on_server_join(server):
        logger.info(f"I joined server {server.name}")
        cache.save('server.json', server.id)
        try:
            bot.resume(config)
        except NotSubscribedToChannelException:
            pass

    @bot.event
    async def on_server_remove(server):
        logger.info(f"I am kicked from server {server.name}.")
        cache.purge('server.json')
        cache.purge('main-channel.json')

    @bot.event
    async def on_message(msg):
        async def say(msg_id, **kwargs):
            await bot.send_message(bot.main_channel, texts[msg_id].format(**kwargs))

        if bot.is_me(msg.author):
            return
        if msg.content == "Please subscribe to here.":
            if not bot.is_owner(msg.author):
                await bot.send_message(bot.main_channel, texts['forbidden'])
            logger.info('Received initialization command')
            cache.save('main-channel.json', msg.channel.id)
            try:
                bot.resume(config)
            except NotSubscribedToChannelException:
                return
            logger.info(f'Subscribed to channel "{bot.main_channel.name}"')
            await say('subscribed')
            return
        if not bot.initialized:
            return
        if not bot.is_eligible(msg.author):
            await say('ineligible', role=bot.anon_role)
        if msg.channel == bot.main_channel:
            bot.record_message(msg)
            await bot.erase_and_repost(msg)
        elif msg.channel.is_private:
            bot.record_dm(msg)
            await bot.forward(msg.content)
            bot.send_message(msg.channel, texts['ack'])

    return bot

if __name__ == '__main__':
    config = get_config(config_path)
    if 'token' not in config or not config['token']:
        logger.error("Token is not filled in! Shutting down now...")
        sys.exit(1)
    bot = initialize(config)
    bot.run(config['token'])
