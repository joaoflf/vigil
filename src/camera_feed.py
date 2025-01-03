from dataclasses import dataclass


@dataclass
class CameraFeed:
    id: str
    name: str
    road: str
    video_source: str
    last_update: int = 0
