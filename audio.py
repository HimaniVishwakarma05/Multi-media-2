"""
audio.py - Sound effects and looping background music for LUMI.

Every sound is generated in code, so no audio files are required. If a file
with the matching name (for example collect.wav) exists in assets/sounds/, that
file is used instead. If the sound device is unavailable, the game runs silently.
"""

import math
import os
import random
from array import array

import pygame

import settings

# Sound effect names used by the game (optional wav files: assets/sounds/<name>.wav)
SOUND_NAMES = ("collect", "crystal", "shield", "block", "hit", "game_over")
MUSIC_NAME = "music"


class AudioManager:
    """
    Owns every sound in the game. Other classes call audio.play("collect")
    and never talk to pygame.mixer directly.
    """

    def __init__(self):
        self.enabled = False          # True only when the sound device works
        self.muted = False            # toggled by the M key
        self.sample_rate = 44100
        self.channels = 2
        self.sounds = {}              # name -> pygame.mixer.Sound
        self.music_sound = None
        self.music_channel = None

        try:
            mixer_info = pygame.mixer.get_init()   # (rate, format, channels) or None
            # Our generated samples are 16-bit signed, so we need format -16.
            if mixer_info is None or mixer_info[1] != -16:
                return                              # no usable sound: run silently

            self.sample_rate, _, self.channels = mixer_info
            pygame.mixer.set_num_channels(8)
            pygame.mixer.set_reserved(1)            # channel 0 is kept for music only
            self.music_channel = pygame.mixer.Channel(0)

            for name in SOUND_NAMES:
                self.sounds[name] = self._build(name)
            self.music_sound = self._build(MUSIC_NAME)
            self.enabled = True
        except pygame.error:
            # Any mixer problem simply turns sound off instead of crashing the game.
            self.enabled = False

    # ------------------------------------------------------------------
    # Public methods used by the rest of the game
    # ------------------------------------------------------------------
    def play(self, name):
        """Play one sound effect. Does nothing when muted or when audio is off."""
        if self.enabled and not self.muted and name in self.sounds:
            self.sounds[name].play()

    def start_music(self):
        """Start the looping background music (called once when the game starts)."""
        if self.enabled and self.music_channel is not None:
            self.music_channel.play(self.music_sound, loops=-1)
            self.music_channel.set_volume(0.0 if self.muted else settings.MUSIC_VOLUME)

    def toggle_mute(self):
        """Switch all sound on or off. Returns True when the game is now muted."""
        self.muted = not self.muted
        if self.enabled and self.music_channel is not None:
            self.music_channel.set_volume(0.0 if self.muted else settings.MUSIC_VOLUME)
        return self.muted

    # ------------------------------------------------------------------
    # Building sounds: use a wav file if present, otherwise generate one
    # ------------------------------------------------------------------
    def _build(self, name):
        path = os.path.join(settings.SOUND_DIR, name + ".wav")
        if os.path.exists(path):
            try:
                return pygame.mixer.Sound(path)
            except pygame.error:
                pass                                # broken file: use the generated sound
        samples = self._make_samples(name)
        return pygame.mixer.Sound(buffer=samples.tobytes())

    def _make_samples(self, name):
        """Return the raw 16-bit samples for one named sound."""
        if name == "collect":                       # bright rising chirp
            return self._render(600, 1200, 0.10, 0.30)
        if name == "crystal":                       # sparkling sweep for the Time Crystal
            return self._render(900, 1800, 0.40, 0.35)
        if name == "shield":                        # warm rising hum for the shield
            return self._render(300, 900, 0.45, 0.35)
        if name == "block":                         # short falling square blip (shield absorbs a hit)
            return self._render(500, 250, 0.18, 0.20, "square")
        if name == "hit":                           # noisy crunch when Lumi takes damage
            return self._render(200, 60, 0.30, 0.45, "noise")
        if name == "game_over":                     # long descending tone
            return self._render(440, 110, 1.20, 0.40)

        # Background music: a short arpeggio in A minor that loops forever.
        samples = array("h")
        for frequency in (220.0, 261.63, 329.63, 440.0, 329.63, 261.63, 196.0, 293.66):
            samples.extend(self._render(frequency, frequency, 0.42, 0.12))
        return samples

    def _render(self, freq_start, freq_end, duration, volume, wave="sine"):
        """
        Create raw samples for one tone.
        - The pitch glides from freq_start to freq_end (a simple sweep).
        - The volume fades out at the end so the sound does not click.
        - Each sample is repeated once per channel (mono or stereo output).
        """
        total = int(self.sample_rate * duration)
        samples = array("h")
        phase = 0.0
        for index in range(total):
            progress = index / max(1, total - 1)                  # 0.0 at start, 1.0 at end
            frequency = freq_start + (freq_end - freq_start) * progress
            phase += 2 * math.pi * frequency / self.sample_rate   # advance the wave

            if wave == "noise":
                raw = random.uniform(-1.0, 1.0)
            elif wave == "square":
                raw = 1.0 if math.sin(phase) >= 0 else -1.0
            else:
                raw = math.sin(phase)

            envelope = (1.0 - progress) ** 2                      # fade out
            value = int(raw * envelope * volume * 32767)          # 16-bit range
            for _ in range(self.channels):
                samples.append(value)
        return samples
