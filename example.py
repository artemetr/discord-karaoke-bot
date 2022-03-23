import os

from discord_karaoke import KaraokeBot, KaraokeBotConfig

KaraokeBot(KaraokeBotConfig.from_config_file('./config.json')) \
    .run(os.getenv('DISCORD_TOKEN'))
