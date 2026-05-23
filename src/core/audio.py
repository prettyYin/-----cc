"""轻量音效播放器：QSoundEffect 包装，缺文件静默，全局静音开关。"""
from __future__ import annotations

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QSoundEffect

from src.core import config
from src.core.paths import assets_dir


_SOUND_FILES = {
    "bark":   "bark.wav",
    "chew":   "chew.wav",
    "notify": "notify.wav",
}


class AudioPlayer(QObject):
    def __init__(self) -> None:
        super().__init__()
        self._effects: dict[str, QSoundEffect] = {}
        self._load_all()

    def _load_all(self) -> None:
        sounds_dir = assets_dir() / "sounds"
        for name, filename in _SOUND_FILES.items():
            path = sounds_dir / filename
            if not path.exists():
                continue
            effect = QSoundEffect(self)
            effect.setSource(QUrl.fromLocalFile(str(path)))
            effect.setVolume(0.3)
            self._effects[name] = effect

    def play(self, name: str) -> None:
        if not config.get("sound_enabled", True):
            return
        effect = self._effects.get(name)
        if effect is None:
            return
        effect.play()


_player: AudioPlayer | None = None


def player() -> AudioPlayer:
    global _player
    if _player is None:
        _player = AudioPlayer()
    return _player


def play(name: str) -> None:
    player().play(name)
