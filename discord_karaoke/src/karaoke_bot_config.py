import json
from dataclasses import dataclass
from typing import Dict


@dataclass
class KaraokeBotConfig:
    guild_id: int
    category_name: str
    text_channel_name: str
    voice_channel_name: str
    admin_role_name: str
    member_role_name: str
    command_prefix: str
    commands: Dict[str, str]
    responses: Dict[str, str]
    text_channel_id: int = None
    voice_channel_id: int = None
    admin_role_id: int = None
    member_role_id: int = None

    @classmethod
    def from_dict(cls, subject: dict):
        return cls(
            guild_id=subject['guild']['id'],
            category_name=subject['guild']['category']['name'],
            text_channel_name=subject['guild']['category']['channels']['text']['name'],
            voice_channel_name=subject['guild']['category']['channels']['voice']['name'],
            admin_role_name=subject['roles']['admin']['name'],
            member_role_name=subject['roles']['member']['name'],
            command_prefix=subject['command_prefix'],
            commands=subject['commands'],
            responses=subject['responses'],
        )

    @classmethod
    def from_config_file(cls, path: str):
        with open(path) as f:
            data = f.read()
        return cls.from_dict(json.loads(data))
