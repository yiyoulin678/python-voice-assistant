from __future__ import annotations

import sys


class MediaKeyError(RuntimeError):
    """媒体键发送失败。"""


def send_media_key(action: str) -> dict[str, str]:
    """发送系统媒体键（播放/暂停、上一首、下一首）。仅 Windows 支持。"""
    normalized = str(action).strip().lower().replace("-", "_")
    vk = _MEDIA_VK.get(normalized)
    if vk is None:
        raise MediaKeyError(f"不支持的媒体操作：{action}")
    if sys.platform != "win32":
        raise MediaKeyError("媒体键控制目前仅支持 Windows。")
    _send_vk_windows(vk)
    return {"action": normalized, "sent": True}


_MEDIA_VK = {
    "play_pause": 0xB3,
    "play": 0xB3,
    "pause": 0xB3,
    "next": 0xB0,
    "next_track": 0xB0,
    "previous": 0xB1,
    "prev": 0xB1,
    "previous_track": 0xB1,
    "stop": 0xB2,
}


def _send_vk_windows(vk: int) -> None:
    import ctypes

    ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong
    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", ctypes.c_ushort),
            ("wScan", ctypes.c_ushort),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", ULONG_PTR),
        ]

    class INPUT(ctypes.Structure):
        class _INPUT(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT)]

        _anonymous_ = ("u",)
        _fields_ = [("type", ctypes.c_ulong), ("u", _INPUT)]

    def _input(vk_code: int, flags: int) -> INPUT:
        return INPUT(
            type=INPUT_KEYBOARD,
            u=INPUT._INPUT(
                ki=KEYBDINPUT(
                    wVk=ctypes.c_ushort(vk_code),
                    wScan=0,
                    dwFlags=flags,
                    time=0,
                    dwExtraInfo=ULONG_PTR(0),
                )
            ),
        )

    inputs = (_input(vk, 0), _input(vk, KEYEVENTF_KEYUP))
    sent = ctypes.windll.user32.SendInput(
        len(inputs),
        ctypes.byref((INPUT * len(inputs))(*inputs)),
        ctypes.sizeof(INPUT),
    )
    if sent != len(inputs):
        raise MediaKeyError("SendInput 未能发送完整媒体键事件。")
