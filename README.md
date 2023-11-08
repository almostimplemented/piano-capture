# Piano Capture

This codebase automates the collection of fine-aligned audio-MIDI data using
(e.g.) a Yamaha Disklavier self-playing piano.

You can download a 16 kHz downsampled monophonic mixture of a re-performance
of the MAESTRO dataset with `piano_capture` on Zenodo (**Studio MAESTRO**: https://zenodo.org/records/10082144).

Recommended installation:
```
pip install -e .
```

Example usage:

```
INPUT_MIDI_ROOT=/path/to/midi_root
OUTPUT_AUDIO_ROOT=/path/to/audio_root
MIDI_OUT_BUS="YAMAHA USB Device Port"
INPUT_AUDIO_DEVICE=0

python -m piano_capture.app \
    $INPUT_MIDI_ROOT \
    $OUTPUT_AUDIO_ROOT \
    $MIDI_OUT_BUS  \
    $INPUT_AUDIO_DEVICE \
    --sample_rate=44100 \
    --num_channels=2 \
    --output_suffix="_v1" \
    --delay-start
```

See `python -m piano_capture.app --help` for further information.

The program will load all MIDI files beneath the specified path and perform 
each on the Disklavier one-by-one. One audio file will be created per input
MIDI file. The hierarchy created beneath the output directory will match that
of the input MIDI directory. 


# FAQ / Issues

> Why would anyone use this?

Excellent question! 
Perhaps you work at a university or research lab focused on music informatics. 
And perhaps you have access to a MIDI-acoustic piano, such as the Yamaha Disklavier.
And perhaps you want to create a dataset of piano audio aligned with MIDI, in order to train automatic piano transcription systems!

During a research collaboration with Yamaha Music Research, I used this code to capture nearly 500 hours of aligned piano data!

> 'MemoryError: Cannot allocate write+execute memory for ffi.callback()'

https://github.com/spatialaudio/python-sounddevice/issues/397

> error: legacy-install-failure
>
> × Encountered error while trying to install package.
>
> ╰─> python-rtmidi

For newer versions of Python, you may need to remove the `python-rtmidi` dependency and install a manual 
```
pip install git+https://github.com/SpotlightKid/python-rtmidi.git@eb16ab3268b29b94cd2baa6bfc777f5cf5f908ba#egg=python-rtmidi
```
(See [this issue](https://github.com/SpotlightKid/python-rtmidi/issues/115) in the python-rtmidi project for more info.)
