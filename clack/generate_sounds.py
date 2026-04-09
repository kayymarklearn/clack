import numpy as np
import wave
import os
from pathlib import Path


def generate_click_sound(filename, duration=0.05, freq=2500, attack=0.002, decay=0.04):
    sample_rate = 44100
    samples = int(duration * sample_rate)

    t = np.linspace(0, duration, samples)

    attack_samples = int(attack * sample_rate)
    decay_samples = int(decay * sample_rate)

    envelope = np.ones(samples)
    envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
    if decay_samples > 0:
        envelope[-decay_samples:] = np.linspace(1, 0, decay_samples)

    noise = np.random.randn(samples) * 0.3
    tone = np.sin(2 * np.pi * freq * t)

    click = (noise * 0.4 + tone * 0.6) * envelope
    click = click * 0.8

    click = np.int16(click * 32767)

    filename = Path(filename)
    os.makedirs(filename.parent, exist_ok=True)
    with wave.open(str(filename), "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(click.tobytes())


def generate_modifier_sound(filename, duration=0.04, freq=1500):
    sample_rate = 44100
    samples = int(duration * sample_rate)

    t = np.linspace(0, duration, samples)

    attack_samples = int(0.001 * sample_rate)
    decay_samples = int(0.035 * sample_rate)

    envelope = np.ones(samples)
    envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
    envelope[-decay_samples:] = np.linspace(1, 0, decay_samples)

    tone = np.sin(2 * np.pi * freq * t)
    noise = np.random.randn(samples) * 0.2

    click = (tone * 0.5 + noise * 0.3) * envelope * 0.5
    click = np.int16(click * 32767)

    filename = Path(filename)
    os.makedirs(filename.parent, exist_ok=True)
    with wave.open(str(filename), "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(click.tobytes())


sounds_dir = Path(__file__).parent / "sounds"

print("Generating clicky (Blue) sounds...")
generate_click_sound(
    sounds_dir / "clicky" / "default.wav",
    duration=0.06,
    freq=2800,
    attack=0.001,
    decay=0.05,
)

print("Generating tactile (Brown) sounds...")
generate_click_sound(
    sounds_dir / "tactile" / "default.wav",
    duration=0.05,
    freq=2000,
    attack=0.002,
    decay=0.04,
)

print("Generating linear (Yellow) sounds...")
generate_click_sound(
    sounds_dir / "linear" / "default.wav",
    duration=0.04,
    freq=1500,
    attack=0.001,
    decay=0.035,
)

print("Generating modifier sounds...")
generate_modifier_sound(
    sounds_dir / "modifier" / "default.wav", duration=0.035, freq=1200
)

print("Done! Generated keyboard click sounds.")
