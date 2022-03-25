from typing import List, Dict

import discord
from discord import VoiceState, Member, User, Role, Guild, DMChannel
from discord.abc import PrivateChannel, GuildChannel
from discord.ext import commands
from discord.ext.commands import Bot, Context

from .decorators import direct_message, allowed_guilds, allowed_channels
from .karaoke_bot_config import KaraokeBotConfig
from .karaoke_log import KaraokeLog


class KaraokeBot:
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

    def get_zero_from_queue(self) -> (User or None, str or None):
        if len(self.queue) >= 1:
            user: User = self.queue[0]
            return user, self.user_songs.get(user.id, None)
        else:
            return None, None

    def get_first_from_queue(self) -> (User or None, str or None):
        if len(self.queue) >= 2:
            user: User = self.queue[1]
            return user, self.user_songs.get(user.id, None)
        else:
            return None, None

    def remove_from_queue(self, user: User, comment: str = None):
        self.queue.remove(user)
        self.user_songs.pop(user.id, None)
        # TODO Добавить коммент

    def get_list_user_description(self, index: int, user: User, comment: str = None) -> str:
        return self.config.responses['list_item'].format(index=index, user=user.mention,
                                                         comment=self.config.responses['list_item_comment'].format(
                                                             comment=comment) if comment else '')

    def get_log(self) -> str:
        return self.config.responses['list_delimiter'].join(
            [self.get_list_user_description(index + 1, log.user, log.comment) for index, log in enumerate(self.log)])

    def get_queue_list(self) -> str:
        return self.config.responses['list_delimiter'].join(
            [self.get_list_user_description(index + 1, user, self.user_songs.get(
                user.id)) for index, user in enumerate(self.queue)])

    @property
    def guild(self) -> Guild:
        return self.bot.get_guild(self.config.guild_id)

    @property
    def admin_role(self) -> Role:
        return discord.utils.get(self.guild.roles, name=self.config.admin_role_name)

    def is_admin_user(self, user: Member) -> bool:
        return self.admin_role in user.roles

    @property
    def member_role(self) -> Role:
        return discord.utils.get(self.guild.roles, name=self.config.member_role_name)

    def is_member_user(self, user: Member) -> bool:
        return self.member_role in user.roles

    @property
    def voice_channel(self):
        return discord.utils.get(self.guild.channels, name=self.config.voice_channel_name)

    @property
    def text_channel(self):
        return discord.utils.get(self.guild.channels, name=self.config.text_channel_name)

    async def change_users_mic_state(self, user_ids: List[int], state: bool):
        for member in self.voice_channel.members:
            if member.id in user_ids:
                if state:
                    await member.edit(mute=False)
                else:
                    await member.edit(mute=True)

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

        @self.bot.command(name=self.config.commands['add_me_to_queue'])
        @direct_message()
        async def add_me_to_queue(ctx: Context, comment: str = None):
            send = ctx.channel.send
            author = ctx.message.author

            if not self.is_user_in_event(author):
                await send(self.config.responses['you_are_not_in_event'].format(channel=self.voice_channel.mention))
            elif author in self.queue:
                await send(self.config.responses['you_are_already_in_queue'].format(index=self.index_in_queue(author)))
            else:
                await send(
                    self.config.responses['you_are_added_in_queue_with_number'].format(
                        index=self.add_to_queue(author, comment)))

        @self.bot.command(name=self.config.commands['show_log_of_artists'])
        @commands.has_role(self.config.admin_role_name)
        @allowed_guilds([self.config.guild_id])
        async def show_log_of_artists(ctx: Context):
            await ctx.message.delete()
            await ctx.channel.send(self.get_log() or self.config.responses['log_empty'])

        @self.bot.command(name=self.config.commands['show_queue_of_artists'])
        async def show_queue_of_artists(ctx: Context):
            author = ctx.message.author

            if type(ctx.channel) is DMChannel:
                await ctx.channel.send(self.get_queue_list() or self.config.responses['queue_is_empty_for_user'])
            elif self.is_event_text_channel(ctx.channel) and self.is_admin_user(author):
                await ctx.message.delete()
                await ctx.channel.send(self.get_queue_list() or self.config.responses['queue_is_empty_for_guild'])

        @self.bot.command(name=self.config.commands['start_performance'])
        @commands.has_role(self.config.admin_role_name)
        @allowed_guilds([self.config.guild_id])
        @allowed_channels(channel_names=[self.config.text_channel_name, self.config.voice_channel_name])
        async def start_performance(ctx: Context):
            await ctx.message.delete()

            user, comment = self.get_zero_from_queue()
            if user:
                await self.change_users_mic_state([user.id], state=True)
                await self.start_artist_performance(user, comment)

                next_user, next_comment = self.get_first_from_queue()
                if next_user:
                    await self.next_artist_performance(next_user, next_comment)
            else:
                await self.queue_is_empty_for_guild()

        @self.bot.command(name=self.config.commands['finish_performance'])
        @commands.has_role(self.config.admin_role_name)
        @allowed_guilds([self.config.guild_id])
        @allowed_channels(channel_names=[self.config.text_channel_name, self.config.voice_channel_name])
        async def finish_performance(ctx: Context):
            await ctx.message.delete()

            if self.queue:
                user, comment = self.pop_from_queue()
                await self.change_users_mic_state([user.id], state=False)
                await self.finish_artist_performance(user, comment)

                next_user, next_comment = self.get_zero_from_queue()
                if next_user:
                    await self.be_ready_artist_performance(next_user, next_comment)
            else:
                await self.queue_is_empty_for_guild()

        @self.bot.command(name=self.config.commands['skip_performance'])
        @commands.has_role(self.config.admin_role_name)
        @allowed_guilds([self.config.guild_id])
        @allowed_channels(channel_names=[self.config.text_channel_name, self.config.voice_channel_name])
        async def skip_performance(ctx: Context, member: discord.Member, comment: str = None):
            await ctx.message.delete()
            user: User = member._user

            if user in self.queue:
                self.change_users_mic_state([user.id], False)
                self.remove_from_queue(user, comment)
                await self.skip_artist_performance(user, comment)
            else:
                await self.user_not_in_queue()

        @self.bot.command(name=self.config.commands['remove_me_from_queue'])
        @direct_message()
        async def remove_me_from_queue(ctx: Context, comment: str = None):
            author = ctx.message.author

            if author in self.queue:
                self.remove_from_queue(author, comment)
                await ctx.channel.send(self.config.responses['your_performance_is_skipped'].format(user=author.mention,
                                                                                                   comment=
                                                                                                   self.config.responses[
                                                                                                       'skip_artist_performance_comment'].format(
                                                                                                       comment=comment) if comment else ''))
            else:
                await ctx.channel.send(self.config.responses['you_are_not_in_queue'])

        @self.bot.command(name=self.config.commands['stop'])
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

            await ctx.channel.send(self.config.responses['event_has_been_stopped'])

            self.log.clear()
            self.queue.clear()
            self.user_songs.clear()

        @self.bot.command(name=self.config.commands['start'])
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

            await ctx.channel.send(self.config.responses['event_has_been_started'])

    async def start_artist_performance(self, user: Member, comment: str = None):
        await user.send(self.config.responses['your_performance_starts_now'])
        await self.text_channel.send(self.config.responses['start_artist_performance'].format(user=user.mention,
                                                                                              comment=
                                                                                              self.config.responses[
                                                                                                  'artist_comment'].format(
                                                                                                  comment=comment) if comment else ''))

    async def skip_artist_performance(self, user: Member, comment: str = None):
        await user.send(self.config.responses['your_performance_is_skipped'].format(comment=self.config.responses[
            'skip_artist_performance_comment'].format(
            comment=comment) if comment else ''))
        await self.text_channel.send(self.config.responses['skip_artist_performance'].format(user=user.mention,
                                                                                             comment=
                                                                                             self.config.responses[
                                                                                                 'skip_artist_performance_comment'].format(
                                                                                                 comment=comment) if comment else ''))

    async def next_artist_performance(self, user: Member, comment: str = None):
        await user.send(self.config.responses['next_performance_is_yours'])
        await self.text_channel.send(self.config.responses['next_artist_performance'].format(user=user.mention,
                                                                                             comment=
                                                                                             self.config.responses[
                                                                                                 'artist_comment'].format(
                                                                                                 comment=comment) if comment else ''))

    async def finish_artist_performance(self, user: Member, comment: str = None):
        await user.send(self.config.responses['your_performance_is_finished'])
        await self.text_channel.send(self.config.responses['finish_artist_performance'].format(user=user.mention,
                                                                                               comment=
                                                                                               self.config.responses[
                                                                                                   'artist_comment'].format(
                                                                                                   comment=comment) if comment else ''))

    async def be_ready_artist_performance(self, user: Member, comment: str = None):
        await user.send(self.config.responses['you_have_to_be_ready_to_perform'])
        await self.text_channel.send(self.config.responses['be_ready_artist_performance'].format(user=user.mention,
                                                                                                 comment=
                                                                                                 self.config.responses[
                                                                                                     'artist_comment'].format(
                                                                                                     comment=comment) if comment else ''))

    async def user_not_in_queue(self):
        await self.text_channel.send(self.config.responses['user_not_in_queue'])

    async def queue_is_empty_for_guild(self):
        await self.text_channel.send(self.config.responses['queue_is_empty_for_guild'])

    def run(self, token: str):
        self.bot = Bot(command_prefix=self.config.command_prefix)
        self.__define_handlers()

        self.bot.run(token)
