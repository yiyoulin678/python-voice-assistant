"""桌面媒体控制（系统媒体键、音乐搜索、正在播放信息）。"""

from app.media.keys import MediaKeyError, send_media_key
from app.media.music import (
    DEFAULT_MUSIC_SOURCE,
    build_music_search_url,
    media_next_track,
    media_play_pause,
    media_previous_track,
    open_music_search,
)
from app.media.now_playing import NowPlayingInfo, read_now_playing

__all__ = [
    "DEFAULT_MUSIC_SOURCE",
    "MediaKeyError",
    "NowPlayingInfo",
    "build_music_search_url",
    "media_next_track",
    "media_play_pause",
    "media_previous_track",
    "open_music_search",
    "read_now_playing",
    "send_media_key",
]
