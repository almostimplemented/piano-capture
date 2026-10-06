import sys
import threading
import time

import mido
import numpy as np
import pytest
import soundfile as sf

from piano_capture import app


class FakeInputStream:
    """Stands in for sounddevice.InputStream: feeds blocks to the callback in real time."""

    block_size = 441

    def __init__(self, device, samplerate, channels, callback, extra_settings):
        self.samplerate = samplerate
        self.channels = channels
        self.callback = callback
        self._stop = threading.Event()

    def __enter__(self):
        self._t0 = time.monotonic()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._thread.join()

    @property
    def time(self):
        return time.monotonic() - self._t0

    def _run(self):
        # Like a real device, deliver however many frames the clock says are due, so
        # the recording length stays correct even if the thread wakes up late (as
        # thread timers often do on macOS).
        block = np.full((self.block_size, self.channels), 0.1, dtype="float32")
        frames_delivered = 0
        while not self._stop.wait(self.block_size / self.samplerate):
            while frames_delivered + self.block_size <= self.time * self.samplerate:
                self.callback(block, self.block_size, None, None)
                frames_delivered += self.block_size


class FakeOutputPort:
    def __init__(self, fail_on_send=None):
        self.sent = []
        self.reset_called = False
        self.fail_on_send = fail_on_send

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def send(self, msg):
        if self.fail_on_send is not None:
            raise self.fail_on_send
        self.sent.append((time.monotonic(), msg))

    def reset(self):
        self.reset_called = True


@pytest.fixture
def midi_file(tmp_path):
    # Two notes over 0.4 seconds (120 bpm, 480 ticks per beat -> 96 ticks = 0.1 s)
    mid = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    track.append(mido.Message("note_on", note=60, velocity=64, time=0))
    track.append(mido.Message("note_off", note=60, velocity=0, time=192))
    track.append(mido.Message("note_on", note=64, velocity=64, time=0))
    track.append(mido.Message("note_off", note=64, velocity=0, time=192))
    mid.tracks.append(track)
    path = tmp_path / "piece.mid"
    mid.save(path)
    return path


@pytest.fixture
def fake_io(monkeypatch):
    port = FakeOutputPort()
    monkeypatch.setattr(app.sd, "InputStream", FakeInputStream)
    monkeypatch.setattr(app, "open_output", lambda name: port)
    monkeypatch.setattr(app, "TAIL_DURATION_SEC", 0.05)
    return port


def test_capture_writes_audio_and_plays_midi_in_time(tmp_path, midi_file, fake_io):
    output = tmp_path / "piece.wav"

    app.capture_performance(midi_file, output, "port", 0, num_channels=2, sample_rate=44100)

    info = sf.info(str(output))
    assert info.channels == 2
    assert info.samplerate == 44100
    assert info.subtype == "PCM_24"
    assert info.duration >= 0.4
    assert not output.with_name("piece.wav.partial").exists()

    messages = [msg for _, msg in fake_io.sent]
    assert [msg.type for msg in messages] == ["note_on", "note_off", "note_on", "note_off"]
    elapsed = fake_io.sent[-1][0] - fake_io.sent[0][0]
    assert elapsed == pytest.approx(0.4, abs=0.05)


def test_failed_capture_leaves_no_file_behind(tmp_path, midi_file, fake_io, monkeypatch):
    class BrokenInputStream(FakeInputStream):
        def __enter__(self):
            raise RuntimeError("audio device went away")

    monkeypatch.setattr(app.sd, "InputStream", BrokenInputStream)
    output = tmp_path / "piece.wav"

    with pytest.raises(RuntimeError):
        app.capture_performance(midi_file, output, "port", 0)

    # Nothing that run() would mistake for a finished recording when resuming
    assert list(tmp_path.glob("*.wav*")) == []


def test_keyboard_interrupt_resets_piano_and_cleans_up(tmp_path, midi_file, monkeypatch):
    port = FakeOutputPort(fail_on_send=KeyboardInterrupt())
    monkeypatch.setattr(app.sd, "InputStream", FakeInputStream)
    monkeypatch.setattr(app, "open_output", lambda name: port)
    output = tmp_path / "piece.wav"

    with pytest.raises(SystemExit) as excinfo:
        app.capture_performance(midi_file, output, "port", 0)

    assert excinfo.value.code == 130
    assert port.reset_called
    assert list(tmp_path.glob("*.wav*")) == []


def test_unreadable_midi_file_is_skipped(tmp_path, fake_io):
    bad_midi = tmp_path / "bad.mid"
    bad_midi.write_bytes(b"not a midi file")
    output = tmp_path / "bad.wav"

    app.capture_performance(bad_midi, output, "port", 0)

    assert not output.exists()
    assert fake_io.sent == []


def test_run_mirrors_hierarchy_and_skips_existing(tmp_path, monkeypatch):
    midi_root = tmp_path / "midi"
    audio_root = tmp_path / "audio"
    for relative in ["2004/a.mid", "2004/b.MID", "2006/c.midi.mid", "2008/d.midi"]:
        (midi_root / relative).parent.mkdir(parents=True, exist_ok=True)
        (midi_root / relative).write_bytes(b"")
    (audio_root / "2004").mkdir(parents=True)
    (audio_root / "2004" / "a_v1.2.wav").write_bytes(b"")

    captured = []
    monkeypatch.setattr(
        app, "capture_performance", lambda midi, audio, *args: captured.append(audio)
    )

    app.run(midi_root, audio_root, "port", 0, realtime=False, output_suffix="_v1.2")

    assert sorted(p.relative_to(audio_root).as_posix() for p in captured) == [
        "2004/b_v1.2.wav",
        "2006/c.midi_v1.2.wav",
        "2008/d_v1.2.wav",
    ]


@pytest.mark.parametrize("cooldown", [None, (30, 3), (15, 0)])
def test_run_refuses_unsafe_cooldown(tmp_path, cooldown):
    with pytest.raises(SystemExit) as excinfo:
        app.run(tmp_path, tmp_path, "port", 0, realtime=False, cooldown_parameters=cooldown)
    assert excinfo.value.code == 1


@pytest.mark.skipif(sys.platform != "darwin", reason="needs macOS")
def test_realtime_and_channel_map_on_macos():
    from piano_capture.darwin_realtime import enable_realtime

    # Runs in a separate thread so the test runner's own thread policy is untouched
    errors = []

    def target():
        try:
            enable_realtime()
        except Exception as e:
            errors.append(e)

    thread = threading.Thread(target=target)
    thread.start()
    thread.join()
    assert errors == []
    assert app._channel_map_settings([2, 3]) is not None


@pytest.mark.skipif(sys.platform == "darwin", reason="behaviour off macOS")
def test_realtime_is_ignored_off_macos(tmp_path):
    app.run(tmp_path, tmp_path, "port", 0, realtime=True)


@pytest.mark.skipif(sys.platform == "darwin", reason="behaviour off macOS")
def test_channel_map_is_rejected_off_macos(tmp_path, capsys):
    with pytest.raises(SystemExit) as excinfo:
        app.run(tmp_path, tmp_path, "port", 0, num_channels=2, channel_map=[2, 3])
    assert excinfo.value.code == 1
    assert "only supported on macOS" in capsys.readouterr().out
