# Piano Capture

This codebase automates the collection of fine-aligned audio-MIDI data using
(e.g.) a Yamaha Disklavier self-playing piano.

You can download a 16 kHz downsampled monophonic mixture of a re-performance
of the MAESTRO dataset with `piano_capture` on Zenodo (**Studio MAESTRO**: https://zenodo.org/records/10082144).

## Installation

```
pip install git+https://github.com/almostimplemented/piano-capture
```

Requires Python 3.9+. Depending on your platform you may also need:

- **PortAudio** (used for audio input): bundled on macOS and Windows; on Linux, `sudo apt install libportaudio2`.
- **ffmpeg** (only for `piano-capture-postprocess`): `brew install ffmpeg` / `sudo apt install ffmpeg`.
- **A compiler, on Python 3.13+**: `python-rtmidi` only ships pre-built wheels up to
  Python 3.12, so on newer versions pip builds it from source. On macOS install the Xcode
  Command Line Tools (`xcode-select --install`); on Linux, a C++ compiler and the ALSA
  headers (`sudo apt install build-essential libasound2-dev`).

For development: `pip install -e ".[test]"` and run `pytest`.

## Usage

List the available MIDI output ports and audio input devices:

```
piano-capture-devices
```

Then start a capture session:

```
INPUT_MIDI_ROOT=/path/to/midi_root
OUTPUT_AUDIO_ROOT=/path/to/audio_root
MIDI_OUT_BUS="YAMAHA USB Device Port"
INPUT_AUDIO_DEVICE=0

piano-capture \
    $INPUT_MIDI_ROOT \
    $OUTPUT_AUDIO_ROOT \
    "$MIDI_OUT_BUS" \
    $INPUT_AUDIO_DEVICE \
    --sample_rate=44100 \
    --num_channels=2 \
    --output_suffix="_v1"
```

See `piano-capture --help` for further information. (`python -m piano_capture` works too.)

The program will load all MIDI files beneath the specified path and perform
each on the Disklavier one-by-one. One audio file will be created per input
MIDI file. The hierarchy created beneath the output directory will match that
of the input MIDI directory.

Files that already exist in the output directory are skipped, so an interrupted
session can be resumed by running the same command again. Recordings are only
moved into place once a performance completes, so a crash or power cut mid-piece
will not leave behind a truncated file that gets skipped on resume.

To protect the Disklavier's thermal relay, the program pauses for 3 minutes after
roughly every 15 minutes of playback (see `--cooldown_parameters`).

### Post-processing

Captured audio is saved untrimmed, at the device's channel count. `piano-capture-postprocess`
trims the playback delay (`--offset_ms`, default 507), mixes the channels down and
resamples every WAV file beneath a directory:

```
piano-capture-postprocess $OUTPUT_AUDIO_ROOT /path/to/processed --sample_rate=16000
```

By default all channels are averaged into a mono file. Pass one weight per input
channel to choose the mix (e.g. `--channel_weights='[0,0,0.8,0.8,0.1,0.1]'` for a
6-channel recording), or use `--stereo` with `--stereo_c0_weights` and
`--stereo_c1_weights` for stereo output.

## Citation

If you use this software, please cite:

```bibtex
@article{edwards2024datadriven,
  title   = {A Data-Driven Analysis of Robust Automatic Piano Transcription},
  author  = {Edwards, Drew and Dixon, Simon and Benetos, Emmanouil and Maezawa, Akira and Kusaka, Yuta},
  journal = {IEEE Signal Processing Letters},
  volume  = {31},
  pages   = {681--685},
  year    = {2024}
}
```

# FAQ / Issues

> Why would anyone use this?

Excellent question!
Perhaps you work at a university or research lab focused on music informatics.
And perhaps you have access to a MIDI-acoustic piano, such as the Yamaha Disklavier.
And perhaps you want to create a dataset of piano audio aligned with MIDI, in order to train automatic piano transcription systems!

During a research collaboration with Yamaha Music Research, I used this code to capture nearly 500 hours of aligned piano data!

> Does it work on Linux / Windows?

Yes, with two options that are macOS-only:
the realtime thread policy (`--realtime`, on by default and skipped elsewhere) and
`--channel_map` (on other platforms, record all channels and select them with
`piano-capture-postprocess`).

> 'MemoryError: Cannot allocate write+execute memory for ffi.callback()'

https://github.com/spatialaudio/python-sounddevice/issues/397

> python-rtmidi fails to install

See the compiler requirements under [Installation](#installation). (See also
[this issue](https://github.com/SpotlightKid/python-rtmidi/issues/115) in the python-rtmidi project.)
