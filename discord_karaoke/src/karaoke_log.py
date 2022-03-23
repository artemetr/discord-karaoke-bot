from dataclasses import dataclass

from discord import User


@dataclass
class KaraokeLog:
    user: User
    comment: str = None
