from __future__ import annotations

import fire
import mido
import sounddevice as sd
import soundfile as sf
import sys
import queue
import time
import numpy as np

from mido import MetaMessage, MidiFile, open_output
from pathlib import Path
from tqdm import tqdm

from piano_capture.util import print_banner
from piano_capture.darwin_realtime import enable_realtime


def capture_performance(
    input_midi_filepath: str,
    output_audio_filepath: str,
    output_port_name: str,
    input_audio_device: int,
    delay_ms: int = 500,
    num_channels: int = 2,
    channel_map: list[int] = None,
    sample_rate: int = 44100,
):
    """Execute a MIDI playback with audio recording session.

    Plays a MIDI file through an output port and simultaneously captures audio data
    from a specified input audio source, writing the resulting wave to disk.

    Args:
        input_midi_filepath:
            Path to MIDI file to play back.
        output_audio_filepath:
            Path to write the captured audio.
        output_port_name:
            Name of the the port where MIDI messages will be sent during playback.
        input_audio_device:
            Physical device number of the input audio source (e.g. microphone).
        delay_ms:
            If there is a fixed delay between the MIDI events and their playback, the
            audio will be trimmed by this amount.
        num_channels:
            Number of channels on the input recording device.
        channel_map:
            List of channels to record. Default is the first num_channels channels.

            Must satisfy num_channels = len(channel_map).
        sample_rate:
            The sample rate to use for the audio recording. Note: the same value will
            be used for opening the input audio stream and for writing the file to disk.
    """
    audio_buffer = []

    if channel_map and num_channels != len(channel_map):
        print(
            f"Error: num_channels ({num_channels}) does not equal len(channel_map) ({len(channel_map)})!"
        )
        return

    def recording_callback(indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        audio_buffer.append(indata.copy())

    try:
        mid = MidiFile(input_midi_filepath)
    except Exception as e:
        print(f"Error opening MIDI file {input_midi_filepath}: ", e)
        print("Skipping")
        return

    core_audio_settings = None
    if channel_map:
        core_audio_settings = sd.CoreAudioSettings(channel_map=channel_map)

    with open_output(output_port_name) as out_port:
        with sf.SoundFile(
            output_audio_filepath,
            mode="w",
            samplerate=sample_rate,
            channels=num_channels,
            subtype="PCM_24",
        ) as file:
            try:
                with sd.InputStream(
                    device=input_audio_device,
                    samplerate=sample_rate,
                    channels=num_channels,
                    callback=recording_callback,
                    extra_settings=core_audio_settings,
                ) as input_stream:
                    # Version of mido.MidiFile.play() to use sounddevice.Stream.time
                    # instead of time.time().
                    #
                    # This allows us to synchronize the MIDI events to the audio stream.

                    start_time = input_stream.time
                    input_time = 0.0

                    for msg in mid:
                        input_time += msg.time
                        playback_time = input_stream.time - start_time
                        duration_to_next_event = input_time - playback_time

                        if duration_to_next_event > 0.0:
                            time.sleep(duration_to_next_event)

                        if isinstance(msg, MetaMessage):
                            continue

                        out_port.send(msg)

                    # Slightly lengthen capture session to avoid any unexpected cutoff
                    # TODO: set this based on delay_ms?
                    time.sleep(3)

                    # Write wavefile to disk
                    for data in audio_buffer:
                        file.write(data)
            except KeyboardInterrupt:
                print()
                print("Tearing down session...")
                file.close()
                Path(file.name).unlink()
                out_port.reset()
                out_port.close()
                sys.exit(130)


def run(
    input_midi_root: str,
    output_audio_root: str,
    output_port_name: str,
    input_audio_device: int,
    delay_ms: int = 500,
    num_channels: int = 2,
    channel_map: list[int] = None,
    sample_rate: int = 44100,
    realtime: bool = True,
    output_suffix: str = "",
    cooldown_parameters: tuple[int] = (15, 3),
):
    """Play MIDI files and record audio for each performance.

    Plays all MIDI files below the specified path an output port and simultaneously
    captures audio data from a specified input audio source, writing one WAV file to
    disk per MIDI file.

    The relative file hierarchy written beneath output_audio_root will match that of
    the input_midi_root hierarchy.

    Args:
        input_midi_root:
            Path to root directory of MIDI files. All files beneath this ending in
            ".mid" will be played in the session.
        output_audio_root:
            Path to the root directory for WAV file output. Each destination filepath
            is derived from the correspondong MIDI file: the relative path will be the
            same but starting from output_audio_root instead of input_midi_root, and
            the file suffix will be ".wav".

            If a file exists at the derived output path, that MIDI file will be
            skipped (useful for resuming large runs).
        output_port_name:
            Name of the the port where MIDI messages will be sent during playback.
        input_audio_device:
            Physical device number of the input audio source (e.g. microphone).
        delay_ms:
            If there is a fixed delay between the MIDI events and their playback, the
            audio will be trimmed by this amount.
        num_channels:
            Number of channels on the input recording device.
        channel_map:
            List of channels to record. Default is the first num_channels channels.

            Must satisfy num_channels = len(channel_map).
        sample_rate:
            The sample rate to use for the audio recording. Note: the same value will
            be used for opening the input audio stream and for writing the file to disk.
        realtime:
            Configure the thread policy for realtime computation. Default is true, but
            only supported on macOS.
        output_suffix:
            Additional suffix to add to output files (before ".wav"). Useful to
            distinguish between (say) different recording conditions.
        cooldown_parameters:
            A tuple of (playtime_min, sleep_min) that instructs the program to sleep for
            sleep_min after (approximately) every playtime_min of playback. This is a safety
            feature to avoid tripping the Disklavier's thermal relay. The default values of
            (15, 3) mean we sleep 3 minutes whenever our playback duration has exceeded 15 minutes
            from the last sleep. We never interrupt a performance, which results in slightly more
            playing time than playtime_min.
    """
    print_banner()
    print()
    print("(To exit, press Ctrl+C)")
    print()

    if channel_map and num_channels != len(channel_map):
        print(
            f"Error: num_channels ({num_channels}) does not equal len(channel_map) ({len(channel_map)})!"
        )
        sys.exit(1)

    if cooldown_parameters is None:
        print("Refusing to run without cooldown limits.")
        sys.exit(1)
    elif cooldown_parameters[0] / cooldown_parameters[1] > 5.0:
        print(
            "Refusing to run with cooldown parameters with a ratio greater than 5-to-1: f{cooldown_parameters}"
        )
        sys.exit(1)

    cooldown_threshold_sec = int(cooldown_parameters[0] * 60)
    cooldown_duration_sec = int(cooldown_parameters[1] * 60)

    midi_root = Path(input_midi_root).absolute()
    audio_root = Path(output_audio_root).absolute()
    midi_filepaths = list(midi_root.rglob("*.[Mm][Ii][Dd]"))
    midi_filepaths = sorted(midi_filepaths, key=lambda p: p.stat().st_size)

    print(f"Preparing to record {len(midi_filepaths)} MIDI files beneath {midi_root}")

    print(
        f"Writing output audio files beneath {audio_root} with suffix {output_suffix}.wav"
    )

    if realtime:
        enable_realtime()

    # Set current time for cooldown timer
    cooldown_timer = time.time()

    for input_midi_filepath in (progress_bar := tqdm(midi_filepaths)):
        if time.time() - cooldown_timer > cooldown_threshold_sec:
            time.sleep(cooldown_duration_sec)
            cooldown_timer = time.time()

        relative_midi_path = input_midi_filepath.relative_to(midi_root)
        relative_audio_path = (
            Path(relative_midi_path)
            .with_name(f"{relative_midi_path.stem}{output_suffix}")
            .with_suffix(f".wav")
        )
        output_audio_filepath = Path(audio_root, relative_audio_path)
        if output_audio_filepath.exists():
            print("Skipping MIDI file because output exists:", output_audio_filepath)
            continue
        Path(output_audio_filepath).parent.mkdir(parents=True, exist_ok=True)
        progress_bar.set_description(f"Processing {relative_midi_path}")
        capture_performance(
            input_midi_filepath,
            output_audio_filepath,
            output_port_name,
            input_audio_device,
            delay_ms,
            num_channels,
            channel_map,
            sample_rate,
        )


if __name__ == "__main__":
    fire.Fire(run)
