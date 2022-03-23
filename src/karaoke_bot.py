from dataclasses import dataclass
from typing import List, Dict

import discord
from discord import VoiceState, Member, User, Role, Guild
from discord.abc import PrivateChannel, GuildChannel
from discord.ext import commands
from discord.ext.commands import Bot, Context

from src import allowed_guilds
from src.decorators import direct_message

message_config = {
    'you_are_not_in_event': 'Для того чтоб участвовать в ивенте необходимо войти в комнату {channel}',
    'you_are_already_in_queue': 'Вы уже участвуете в караоке. Ваш номер в очереди {index}',
    'you_are_not_in_queue': 'Вы не находитесь в очереди',
    'you_are_added_in_queue_with_number': 'Вы добавлены в очередь. Ваш номер в очереди {index}',
    'list_item': '{index} - {user}{comment}',
    'list_item_comment': ' - {comment}',
    'list_delimiter': '\n',
    'queue_is_empty_for_user': 'Очередь пуста. Вы можете быть первым!',
    'queue_is_empty_for_guild': 'Очередь пока пуста!',
    'current_artist': 'Для вас выступает {user}{comment}',
    'next_artist': 'Следующий {user}{comment}',
    'artist_comment': ' - {comment}',
    'user_not_in_queue': 'Пользователь не находится в очереди',
    'user_remove_from_queue': 'Пользователь {user} был удалён из очереди{comment}.',
    'user_remove_from_queue_comment': ' по причине {comment}',
    'event_has_been_stopped': 'Ивент был остановлен',
    'event_has_been_started': 'Ивент запущен',
    'log_empty': 'История караоке пуста',
}

command_config = {
    'append': 'append',
    'log': 'log',
    'list': 'list',
    'dm_list': 'dm_list',
    'pop': 'pop',
    'remove': 'remove',
    'stop': 'stop',
    'start': 'start',
    'cancel': 'cancel',
}


@dataclass
class KaraokeBotConfig:
    guild_id: int
    command_prefix: str = '?'
    text_channel_name: str = '🎉-ивент-караоке'
    text_channel_id: int = None
    voice_channel_name: str = '🎉 Ивент "Караоке"'
    voice_channel_id: int = None
    category_name: str = '---- • ИГРАЕМ 🎉'
    admin_role_name: str = 'karaoke-admin'
    admin_role_id: int = None
    member_role_name: str = 'karaoke-member'
    member_role_id: int = None


@dataclass
class KaraokeLog:
    user: User
    comment: str = None


class Karaoke:
    def __init__(self, config: KaraokeBotConfig):
        self.config = config
        self.bot: Bot = None
        self.queue: List[User] = []
        self.user_songs: Dict[int, str] = dict()
        self.log: List[KaraokeLog] = []

    def index_in_queue(self, user: discord.abc.User) -> int:
        return self.queue.index(user) + 1

    def add_to_queue(self, user: User, comment: str = None) -> int:
        self.queue.append(user)
        if comment:
            self.user_songs[user.id] = comment

        return self.index_in_queue(user)

    def add_to_log(self, user, comment: str = None):
        self.log.append(KaraokeLog(user, comment))

    def pop_from_queue(self) -> (User, str or None):
        user: User = self.queue.pop(0)
        self.add_to_log(user, self.user_songs.get(user.id))
        return user, self.user_songs.pop(user.id, None)

    def get_zero_from_queue(self) -> (User, str or None):
        user: User = self.queue[0]
        return user, self.user_songs.get(user.id, None)

    def remove_from_queue(self, user: User, comment: str = None):
        self.queue.remove(user)
        self.user_songs.pop(user.id, None)
        # TODO Добавить коммент

    def get_list_user_description(self, index: int, user: User, comment: str = None) -> str:
        return message_config['list_item'].format(index=index, user=user.mention,
                                                  comment=message_config['list_item_comment'].format(
                                                      comment=comment) if comment else '')

    def get_log(self) -> str:
        return message_config['list_delimiter'].join(
            [self.get_list_user_description(index + 1, log.user, log.comment) for index, log in enumerate(self.log)])

    def get_queue_list(self) -> str:
        return message_config['list_delimiter'].join(
            [self.get_list_user_description(index + 1, user, self.user_songs.get(
                user.id)) for index, user in enumerate(self.queue)])

    @property
    def guild(self) -> Guild:
        return self.bot.get_guild(self.config.guild_id)

    @property
    def admin_role(self) -> Role:
        return discord.utils.get(self.guild.roles, name=self.config.admin_role_name)

    @property
    def member_role(self) -> Role:
        return discord.utils.get(self.guild.roles, name=self.config.member_role_name)

    @property
    def voice_channel(self):
        return discord.utils.get(self.guild.channels, name=self.config.voice_channel_name)

    async def __define_roles(self):
        guild = self.guild

        if not self.admin_role:
            self.config.admin_role_id = (await guild.create_role(name=self.config.admin_role_name)).id

        if not self.member_role:
            self.config.member_role_id = (await guild.create_role(name=self.config.member_role_name)).id

    def is_event_guild(self, guild: Guild) -> bool:
        return guild.id == self.config.guild_id

    def is_event_voice_channel(self, channel: GuildChannel or PrivateChannel) -> bool:
        return channel.id == self.config.voice_channel_id

    def is_event_text_channel(self, channel: GuildChannel or PrivateChannel) -> bool:
        return channel.id == self.config.text_channel_id

    async def apply_roles(self, member: Member, before: VoiceState, after: VoiceState):
        if after.channel and self.is_event_guild(after.channel.guild) and self.is_event_voice_channel(after.channel):
            await member.add_roles(self.member_role)
        elif before.channel and self.is_event_guild(before.channel.guild) and self.is_event_voice_channel(
                before.channel):
            await member.remove_roles(self.member_role)

    def is_user_in_event(self, user: User) -> bool:
        return bool(discord.utils.get(self.voice_channel.members, id=user.id))

    def __define_handlers(self):
        @self.bot.event
        async def on_ready():
            await self.__define_roles()

        @self.bot.event
        async def on_voice_state_update(member: Member, before: VoiceState, after: VoiceState):
            await self.apply_roles(member, before, after)

        @self.bot.command(name=command_config['append'])
        @direct_message()
        async def queue_append(ctx: Context, comment: str = None):
            send = ctx.channel.send
            author = ctx.message.author

            if not self.is_user_in_event(author):
                await send(message_config['you_are_not_in_event'].format(channel=self.voice_channel.mention))
            elif author in self.queue:
                await send(message_config['you_are_already_in_queue'].format(index=self.index_in_queue(author)))
            else:
                await send(
                    message_config['you_are_added_in_queue_with_number'].format(
                        index=self.add_to_queue(author, comment)))

        @self.bot.command(name=command_config['log'])
        @commands.has_role(self.config.admin_role_name)
        @allowed_guilds([self.config.guild_id])
        async def event_log(ctx: Context):
            await ctx.message.delete()
            await ctx.channel.send(self.get_log() or message_config['log_empty'])

        @self.bot.command(name=command_config['list'])
        @commands.has_role(self.config.admin_role_name)
        @allowed_guilds([self.config.guild_id])
        async def queue_guild_list(ctx: Context):
            await ctx.message.delete()
            await ctx.channel.send(self.get_queue_list() or message_config['queue_is_empty_for_guild'])

        @self.bot.command(name=command_config['dm_list'])
        @direct_message()
        async def queue_user_list(ctx: Context):
            await ctx.channel.send(self.get_queue_list() or message_config['queue_is_empty_for_user'])

        @self.bot.command(name=command_config['pop'])
        @commands.has_role(self.config.admin_role_name)
        @allowed_guilds([self.config.guild_id])
        async def queue_pop(ctx: Context):
            await ctx.message.delete()

            if self.queue:
                user, comment = self.pop_from_queue()
                await ctx.channel.send(message_config['current_artist'].format(user=user.mention,
                                                                               comment=message_config[
                                                                                   'artist_comment'].format(
                                                                                   comment=comment) if comment else ''))

                if self.queue:
                    next_user, next_comment = self.get_zero_from_queue()
                    await ctx.channel.send(message_config['next_artist'].format(user=next_user.mention,
                                                                                comment=message_config[
                                                                                    'artist_comment'].format(
                                                                                    comment=next_comment) if next_comment else ''))
            else:
                await ctx.channel.send(message_config['queue_is_empty_for_guild'])

        @self.bot.command(name=command_config['remove'])
        @commands.has_role(self.config.admin_role_name)
        @allowed_guilds([self.config.guild_id])
        async def queue_exclude(ctx: Context, member: discord.Member, comment: str = None):
            await ctx.message.delete()
            user: User = member._user

            if user in self.queue:
                self.remove_from_queue(user, comment)
                await ctx.channel.send(message_config['user_remove_from_queue'].format(user=user.mention,
                                                                                       comment=message_config[
                                                                                           'user_remove_from_queue_comment'].format(
                                                                                           comment=comment) if comment else ''))
            else:
                await ctx.channel.send(message_config['user_not_in_queue'])

        @self.bot.command(name=command_config['cancel'])
        @direct_message()
        async def queue_append(ctx: Context, comment: str = None):
            author = ctx.message.author

            if author in self.queue:
                self.remove_from_queue(author, comment)
                await ctx.channel.send(message_config['user_remove_from_queue'].format(user=author.mention,
                                                                                       comment=message_config[
                                                                                           'user_remove_from_queue_comment'].format(
                                                                                           comment=comment) if comment else ''))
            else:
                await ctx.channel.send(message_config['you_are_not_in_queue'])

        @self.bot.command(name=command_config['stop'])
        @commands.has_role(self.config.admin_role_name)
        @allowed_guilds([self.config.guild_id])
        async def stop_karaoke(ctx: Context):
            guild = ctx.guild

            text_channel = discord.utils.get(guild.text_channels, name=self.config.text_channel_name)
            if text_channel:
                await text_channel.delete()

            voice_channel = discord.utils.get(guild.voice_channels, name=self.config.voice_channel_name)
            if voice_channel:
                await voice_channel.delete()

            await ctx.channel.send(message_config['event_has_been_stopped'])

            self.log.clear()
            self.queue.clear()
            self.user_songs.clear()

        @self.bot.command(name=command_config['start'])
        @commands.has_role(self.config.admin_role_name)
        @allowed_guilds([self.config.guild_id])
        async def start_karaoke(ctx: Context):
            guild = ctx.guild
            category = discord.utils.get(guild.categories, name=self.config.category_name)

            if not category:
                category = await guild.create_category(self.config.category_name)

            text_channel = discord.utils.get(guild.text_channels, name=self.config.text_channel_name)
            if not text_channel:
                text_channel = await guild.create_text_channel(self.config.text_channel_name, category=category,
                                                               overwrites={
                                                                   guild.default_role: discord.PermissionOverwrite(
                                                                       read_messages=False, connect=False),
                                                                   self.member_role: discord.PermissionOverwrite(
                                                                       read_messages=True, send_messages=True,
                                                                       connect=True, speak=False),
                                                                   self.admin_role: discord.PermissionOverwrite(
                                                                       read_messages=True, send_messages=True,
                                                                       connect=True, speak=True)
                                                               })
            self.config.text_channel_id = text_channel.id

            voice_channel = discord.utils.get(guild.text_channels, name=self.config.voice_channel_name)
            if not voice_channel:
                voice_channel = await guild.create_voice_channel(self.config.voice_channel_name, category=category,
                                                                 overwrites={
                                                                     guild.default_role: discord.PermissionOverwrite(
                                                                         connect=True, speak=False),
                                                                     self.member_role: discord.PermissionOverwrite(
                                                                         connect=True, speak=False),
                                                                     self.admin_role: discord.PermissionOverwrite(
                                                                         connect=True, speak=True)
                                                                 })
            self.config.voice_channel_id = voice_channel.id

            await ctx.channel.send(message_config['event_has_been_started'])

    def run(self, token: str):
        self.bot = Bot(command_prefix=self.config.command_prefix)
        self.__define_handlers()

        self.bot.run(token)
