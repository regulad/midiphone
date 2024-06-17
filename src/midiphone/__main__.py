"""CLI for MIDIPhone - Reconstruct MIDI notes over a virtual device from a live audio stream.

Copyright (C) 2024  Parker Wahle

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""  # noqa: E501, B950

from __future__ import annotations

import logging
import os
import shelve
import tkinter as tk
from pathlib import Path
from shelve import Shelf
from threading import Thread
from typing import Callable

import numpy as np
import pyaudio
import scipy
import typer
from mido import Message as MidiMessage
from pytemidi import Device as MidiDevice
from rich.logging import RichHandler

from ._metadata import __title__

cli = typer.Typer()

PYAUDIO_CHUNK_SIZE = 1024
PYAUDIO_FORMAT = pyaudio.paInt16
PYAUDIO_SAMPLE_RATE = 44100
PYAUDIO_INPUT_DEVICE_INDEX = 6
NUMPY_DTYPE = np.int16

# regular keyboard range
MIDI_NOTE_MIN = 21
MIDI_NOTE_MAX = 108

# maximum magnitude of the fft output
MAX_MAGNITUDE = 4_000_000  # somewhat arbitrarily chosen


def get_midi_note_for_frequency(frequency: np.float64) -> int:
    return int(round(69 + 12 * np.log2(frequency / 440), 0))


def get_frequency_for_midi_note(note: int) -> float:
    return 440 * 2 ** ((note - 69) / 12)


def get_note_name_for_midi_note(note: int) -> str:
    """
    Convert a MIDI note to a note name.
    """
    note_names = [
        "C",
        "C#",
        "D",
        "D#",
        "E",
        "F",
        "F#",
        "G",
        "G#",
        "A",
        "A#",
        "B",
    ]
    return f"{note_names[note % 12]}{note // 12 - 1}"


def seconds_to_frames(seconds: float) -> int:
    return int(seconds * PYAUDIO_SAMPLE_RATE // PYAUDIO_CHUNK_SIZE)


class MicrophoneToMidiThread(Thread):
    def __init__(self, midi_device: MidiDevice, pyaudio_stream: pyaudio.Stream, config: Shelf,
                 update_minimum_or_maximum_magnitude_callback: Callable[[], None] | None = None):
        super().__init__(daemon=True)

        self.should_die = False

        self.config = config

        self.midi_device = midi_device
        self.pyaudio_stream = pyaudio_stream
        self.notes_on = set()

        self.should_listen_for_minimum_magnitude_frames = 0
        self.minimum_magnitude = config.get("minimum_magnitude", 0.0)
        self.should_listen_for_maximum_magnitude_frames = 0
        self.maximum_magnitude = config.get("maximum_magnitude", MAX_MAGNITUDE)

        self.keyboard_has_velocity = config.get("keyboard_has_velocity", False)
        self.velocity_threshold = config.get("velocity_threshold", 64)

        self.update_minimum_or_maximum_magnitude_callback: Callable[
                                                               [], None] | None = update_minimum_or_maximum_magnitude_callback

    def write_config(self):
        self.config["minimum_magnitude"] = self.minimum_magnitude
        self.config["maximum_magnitude"] = self.maximum_magnitude
        self.config["keyboard_has_velocity"] = self.keyboard_has_velocity
        self.config["velocity_threshold"] = self.velocity_threshold

    def read_one_frame(self):
        audio_data = self.pyaudio_stream.read(PYAUDIO_CHUNK_SIZE)
        N = len(audio_data)

        notes_seen = set()

        # convert into a numpy array
        numpy_array = np.frombuffer(audio_data, dtype=NUMPY_DTYPE)

        # run FFT
        yf = scipy.fft.fft(numpy_array)  # real: sine, imaginary: cosine
        xf = scipy.fft.fftfreq(N, 1 / PYAUDIO_SAMPLE_RATE)  # frequency bins

        # Take the absolute value to get the magnitude
        yf_magnitude = np.abs(yf)

        # Get the positive frequencies
        xf_positive = xf[:N // 2]
        yf_positive_magnitude = yf_magnitude[:N // 2]

        # adjust sensitivity automatically
        minimum_magnitude_before = self.minimum_magnitude
        maximum_magnitude_before = self.maximum_magnitude
        should_write_config = False
        if self.should_listen_for_maximum_magnitude_frames == 1 or self.should_listen_for_minimum_magnitude_frames == 1:
            # this is the last frame we should listen for
            should_write_config = True
        if self.should_listen_for_minimum_magnitude_frames > 0:
            self.minimum_magnitude = np.max(yf_positive_magnitude)
            self.should_listen_for_minimum_magnitude_frames -= 1
        if self.should_listen_for_maximum_magnitude_frames > 0:
            self.maximum_magnitude = np.max(yf_positive_magnitude)
            self.should_listen_for_maximum_magnitude_frames -= 1
        if self.minimum_magnitude != minimum_magnitude_before or self.maximum_magnitude != maximum_magnitude_before:
            if self.update_minimum_or_maximum_magnitude_callback is not None:
                self.update_minimum_or_maximum_magnitude_callback()
        if should_write_config:
            self.write_config()

        # find local maxima
        peaks, _ = scipy.signal.find_peaks(yf_positive_magnitude)

        # for each peak, find the corresponding MIDI note
        for peak in peaks:  # type: ignore
            # adjust sensitivity automatically

            frequency = xf_positive[peak]
            magnitude = yf_positive_magnitude[peak]

            if magnitude < self.minimum_magnitude:
                continue

            note = get_midi_note_for_frequency(frequency)

            if note > 127:
                continue  # ignore notes above 127

            velocity = int(
                127 * (magnitude - self.minimum_magnitude) / (self.maximum_magnitude - self.minimum_magnitude))

            if velocity < 0:
                velocity = 0
            elif velocity > 127:
                velocity = 127

            if not self.keyboard_has_velocity:
                if velocity < self.velocity_threshold:
                    continue
                velocity = 127

            notes_seen.add(note)

            if note in self.notes_on:
                continue

            midi_message = MidiMessage("note_on", note=note, velocity=velocity)

            self.midi_device.send(midi_message.bin())
            logging.info(f"Note On: {get_note_name_for_midi_note(note)} ({note}), Velocity: {velocity}")

            self.notes_on.add(note)

        notes_off = self.notes_on - notes_seen
        for note in notes_off:
            midi_message = MidiMessage("note_off", note=note, velocity=0)
            self.midi_device.send(midi_message.bin())
            logging.info(f"Note Off: {get_note_name_for_midi_note(note)} ({note})")
            self.notes_on.remove(note)

    def run(self):
        while not self.should_die:
            try:
                self.read_one_frame()
            except Exception as e:
                logging.exception(e)


def create_window(config: Shelf) -> tk.Tk:
    window = tk.Tk()
    window.title(__title__)

    midiphone_midi_device = MidiDevice("MIDIPhone")
    midiphone_midi_device.create()

    p = pyaudio.PyAudio()

    pyaudio_info = p.get_host_api_info_by_index(0)
    pyaudio_device_count = pyaudio_info.get("deviceCount")

    pyaudio_devices: list[tuple[int, str]] = []

    for i in range(pyaudio_device_count):
        pyaudio_device_info = p.get_device_info_by_host_api_device_index(0, i)
        if pyaudio_device_info.get("maxInputChannels") > 0:
            pyaudio_devices.append((i, pyaudio_device_info.get("name")))

    # add a label saying that the user should select the input device
    label = tk.Label(window, text="Please select the input device:")
    label.pack()

    # make a dropdown menu for the user to select the input device
    selected_device = tk.StringVar(window)
    last_selected_device = config.get("selected_device", 0)
    selected_device.set(pyaudio_devices[last_selected_device][1])
    dropdown = tk.OptionMenu(window, selected_device, *[device[1] for device in pyaudio_devices])
    dropdown.pack()

    thread: MicrophoneToMidiThread | None = None

    def update_input_device_index():
        nonlocal thread
        for device_index, device in pyaudio_devices:
            if device == selected_device.get():
                config["selected_device"] = device_index
                if thread is not None:
                    thread.should_die = True
                    thread.join()
                stream = p.open(
                    format=PYAUDIO_FORMAT,
                    channels=1,
                    rate=PYAUDIO_SAMPLE_RATE,
                    input=True,
                    output=False,
                    frames_per_buffer=PYAUDIO_CHUNK_SIZE,
                    input_device_index=device_index,
                )

                def update_minimum_or_maximum_magnitude_callback():
                    minimum_magnitude.set(thread.minimum_magnitude)
                    maximum_magnitude.set(thread.maximum_magnitude)

                thread = MicrophoneToMidiThread(midiphone_midi_device, stream, config,
                                                update_minimum_or_maximum_magnitude_callback)
                thread.minimum_magnitude = minimum_magnitude.get()
                thread.maximum_magnitude = maximum_magnitude.get()
                thread.keyboard_has_velocity = keyboard_has_velocity.get()
                thread.velocity_threshold = velocity_threshold.get()
                thread.write_config()
                thread.start()
                update_status()
                return

    selected_device.trace_add("write", lambda _1, _2, _3: update_input_device_index())

    # add a button to update the input device
    button = tk.Button(window, text="Start/Restart", command=update_input_device_index)
    button.pack()

    # add a status label
    status_label = tk.Label(window, text="Not listening for audio")
    status_label.pack()

    def update_status():
        nonlocal thread
        if thread is not None:
            status_label.config(text="Listening for audio...")
        else:
            status_label.config(text="Not listening for audio")

    # add a slider to adjust the minimum magnitude
    minimum_magnitude = tk.DoubleVar(window)

    def set_minimum_magnitude(*args) -> None:
        if thread is not None:
            thread.minimum_magnitude = minimum_magnitude.get()
            thread.write_config()

    minimum_magnitude.trace_add("write", set_minimum_magnitude)
    minimum_magnitude_frame = tk.Frame(window)
    minimum_magnitude.set(config.get("minimum_magnitude", 0.0))
    minimum_magnitude_label = tk.Label(minimum_magnitude_frame, text="Minimum Magnitude")
    minimum_magnitude_label.pack()
    minimum_magnitude_slider_frame = tk.Frame(minimum_magnitude_frame)
    minimum_magnitude_slider = tk.Scale(window, from_=0.0, to=MAX_MAGNITUDE, resolution=0.01, orient=tk.HORIZONTAL,
                                        variable=minimum_magnitude)
    minimum_magnitude_slider.pack()
    listen_for_minimum_magnitude = tk.Button(minimum_magnitude_slider_frame, text="Listen for Minimum Magnitude")

    def toggle_listen_for_minimum_magnitude():
        if thread is not None:
            if thread.should_listen_for_minimum_magnitude_frames > 0:
                thread.should_listen_for_minimum_magnitude_frames = 0
            else:
                thread.should_listen_for_minimum_magnitude_frames = seconds_to_frames(5)

    listen_for_minimum_magnitude.config(command=toggle_listen_for_minimum_magnitude)
    listen_for_minimum_magnitude.pack()
    minimum_magnitude_slider_frame.pack()
    minimum_magnitude_frame.pack()

    # add a slider to adjust the maximum magnitude
    maximum_magnitude = tk.DoubleVar(window)

    def set_maximum_magnitude(*args) -> None:
        if thread is not None:
            thread.maximum_magnitude = maximum_magnitude.get()
            thread.write_config()

    maximum_magnitude.trace_add("write", set_maximum_magnitude)
    maximum_magnitude_frame = tk.Frame(window)
    maximum_magnitude.set(config.get("maximum_magnitude", MAX_MAGNITUDE))
    maximum_magnitude_label = tk.Label(maximum_magnitude_frame, text="Maximum Magnitude")
    maximum_magnitude_label.pack()
    maximum_magnitude_slider_frame = tk.Frame(maximum_magnitude_frame)
    maximum_magnitude_slider = tk.Scale(window, from_=0.0, to=MAX_MAGNITUDE, resolution=0.01, orient=tk.HORIZONTAL,
                                        variable=maximum_magnitude)
    maximum_magnitude_slider.pack()
    listen_for_maximum_magnitude = tk.Button(maximum_magnitude_slider_frame, text="Listen for Maximum Magnitude")

    def toggle_listen_for_maximum_magnitude() -> None:
        if thread is not None:
            if thread.should_listen_for_maximum_magnitude_frames > 0:
                thread.should_listen_for_maximum_magnitude_frames = 0
            else:
                thread.should_listen_for_maximum_magnitude_frames = seconds_to_frames(5)

    listen_for_maximum_magnitude.config(command=toggle_listen_for_maximum_magnitude)
    listen_for_maximum_magnitude.pack()
    maximum_magnitude_slider_frame.pack()
    maximum_magnitude_frame.pack()

    # add a checkbox to enable velocity
    keyboard_has_velocity = tk.BooleanVar(window)
    keyboard_has_velocity.set(config.get("keyboard_has_velocity", False))

    def toggle_keyboard_has_velocity(*args) -> None:
        if thread is not None:
            thread.keyboard_has_velocity = keyboard_has_velocity.get()
            thread.write_config()

    keyboard_has_velocity.trace_add("write", toggle_keyboard_has_velocity)
    keyboard_has_velocity_frame = tk.Frame(window)
    keyboard_has_velocity_label = tk.Label(keyboard_has_velocity_frame, text="Keyboard Has Velocity")
    keyboard_has_velocity_label.pack(side=tk.LEFT)
    keyboard_has_velocity_checkbox = tk.Checkbutton(keyboard_has_velocity_frame, variable=keyboard_has_velocity)
    keyboard_has_velocity_checkbox.pack(side=tk.RIGHT)
    keyboard_has_velocity_frame.pack()

    # add a slider to adjust the velocity threshold
    velocity_threshold = tk.IntVar(window)

    def set_velocity_threshold(*args) -> None:
        if thread is not None:
            thread.velocity_threshold = velocity_threshold.get()
            thread.write_config()

    velocity_threshold.trace_add("write", set_velocity_threshold)
    velocity_threshold_frame = tk.Frame(window)
    velocity_threshold.set(config.get("velocity_threshold", 64))
    velocity_threshold_label = tk.Label(velocity_threshold_frame, text="Velocity Threshold")
    velocity_threshold_label.pack()
    velocity_threshold_slider_frame = tk.Frame(velocity_threshold_frame)
    velocity_threshold_slider = tk.Scale(window, from_=0, to=127, orient=tk.HORIZONTAL, variable=velocity_threshold)
    velocity_threshold_slider.pack()
    velocity_threshold_slider_frame.pack()
    velocity_threshold_frame.pack()

    return window


@cli.command()
def main() -> None:
    # only works on Windows
    if os.name != "nt":
        raise NotImplementedError("This program only works on Windows.")

    logging.basicConfig(handlers=(RichHandler(),), level=logging.INFO)

    config_path = Path(os.getenv("APPDATA")) / __title__
    config_path.mkdir(exist_ok=True)

    with shelve.open(str(config_path / "config")) as config:
        window = create_window(config)
        window.mainloop()


if __name__ == "__main__":  # pragma: no cover
    cli()

__all__ = ("cli",)
