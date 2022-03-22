import os

import discord
from discord import Client, VoiceState, Member
from discord.ext import commands
from discord.ext.commands import Bot, Context

from src import allowed_guilds
from src.decorators import direct_message


class Karaoke:
    def __init__(self, guild_id, command_prefix: str = '?', text_channel_name: str = '🎉-ивент-караоке',
                 voice_channel_name: str = '🎉 Ивент "Караоке"', category_name: str = '---- • ИГРАЕМ 🎉',
                 role_name: str = 'karaoke-bot'):
        self.guild_id = guild_id
        self.command_prefix = command_prefix

        self.text_channel_name = text_channel_name
        self.voice_channel_name = voice_channel_name
        self.category_name = category_name
        self.role_name = role_name
        self.role_id: int = None
        self.text_channel_id: int = None
        self.voice_channel_id: int = None

        self.client: Client = None
        self.bot: Bot = None

        self.queue = []

    def __define_main_handlers(self):
        @self.bot.event
        async def on_ready():
            guild = self.bot.get_guild(self.guild_id)

            karaoke_role = discord.utils.get(guild.roles, name=self.role_name)
            if not karaoke_role:
                karaoke_role = await guild.create_role(name=self.role_name)

            self.role_id = karaoke_role.id

        @self.bot.event
        async def on_voice_state_update(member: Member, before: VoiceState, after: VoiceState):
            if after.channel.guild.id == self.guild_id and after.channel.name == self.voice_channel_name:
                await member.add_roles(discord.utils.get(after.channel.guild.roles, name=self.role_name))
            elif before.channel.guild.id == self.guild_id and before.channel.name == self.voice_channel_name:
                await member.remove_roles(discord.utils.get(before.channel.guild.roles, name=self.role_name))

        @self.bot.command(name='append')
        @direct_message()
        async def query_append(ctx: Context):
            author = ctx.message.author
            channel = ctx.message.channel

            if author in self.queue:
                await channel.send(f'Вы уже находитесь в очереди, ваш номер {self.queue.index(author) + 1}!')
            else:
                self.queue.append(author)
                await channel.send(f'Вы были добавлены в очередь, ваш номер {self.queue.index(author) + 1}!')

        @self.bot.command(name='show')
        @commands.has_role('admin')
        @allowed_guilds([self.guild_id])
        async def queue_show(ctx: Context):
            await ctx.channel.send('\n'.join([f'{index + 1}. {user.mention}' for index, user in enumerate(
                self.queue)]) if self.queue else 'Очередь пуста. Вы можете быть первым!')

        @self.bot.command(name='list')
        @direct_message()
        async def queue_show_dm(ctx: Context):
            await ctx.channel.send('\n'.join([f'{index + 1}. {user.mention}' for index, user in enumerate(
                self.queue)]) if self.queue else 'Очередь пуста. Вы можете быть первым!')

        @self.bot.command(name='pop')
        @commands.has_role('admin')
        @allowed_guilds([self.guild_id])
        async def queue_pop(ctx: Context):
            await ctx.message.delete()

            user = self.queue.pop(0) if self.queue else None
            if user:
                await ctx.channel.send(f'Для вас выступает {user.mention}.')
            else:
                await ctx.channel.send('А очередь то пустует!')

        @self.bot.command(name='exclude')
        @commands.has_role('admin')
        @allowed_guilds([self.guild_id])
        async def queue_exclude(ctx: Context, member: discord.Member, reason: str = ''):
            await ctx.message.delete()

            if member._user in self.queue:
                self.queue.remove(member._user)
                await ctx.channel.send(f'Пользователь {member._user.mention} был удалён по причине {reason}')
            else:
                await ctx.channel.send(f'Пользователь не находится в очереди караоке')


        @self.bot.command(name='stop')
        @commands.has_role('admin')
        @allowed_guilds([self.guild_id])
        async def stop_karaoke(ctx: Context):
            guild = ctx.guild

            text_channel = discord.utils.get(guild.text_channels, name=self.text_channel_name)
            if text_channel:
                await text_channel.delete()

            voice_channel = discord.utils.get(guild.voice_channels, name=self.voice_channel_name)
            if voice_channel:
                await voice_channel.delete()

            await ctx.channel.send('Ивент остановлен')

        @self.bot.command(name='start')
        @commands.has_role('admin')
        @allowed_guilds([self.guild_id])
        async def start_karaoke(ctx: Context):
            guild = ctx.guild
            category = discord.utils.get(guild.categories, name=self.category_name)
            if not category:
                category = await guild.create_category(self.category_name)

            text_channel = discord.utils.get(guild.text_channels, name=self.text_channel_name)
            if not text_channel:
                text_channel = await guild.create_text_channel(self.text_channel_name, category=category, overwrites={
                    guild.default_role: discord.PermissionOverwrite(
                        read_messages=False, connect=False),
                    discord.utils.get(guild.roles,
                                      name=self.role_name): discord.PermissionOverwrite(
                        read_messages=True, send_messages=True,
                        connect=True, speak=True)
                })
            self.text_channel_id = text_channel.id

            voice_channel = discord.utils.get(guild.text_channels, name=self.voice_channel_name)
            if not voice_channel:
                voice_channel = await guild.create_voice_channel(self.voice_channel_name, category=category)
            self.voice_channel_id = voice_channel.id

            await ctx.channel.send('Ивент запущен')

        # @self.bot.event
        # async def on_message(message: Message):
        #     if message.author.id == self.bot.user.id:
        #         return
        #
        #     if type(message.channel) is DMChannel:
        #

    def run(self, token: str):
        self.bot = Bot(command_prefix=self.command_prefix)
        self.__define_main_handlers()

        self.bot.run(token)


Karaoke(guild_id=952993401836556379) \
    .run(os.getenv('DISCORD_TOKEN'))
