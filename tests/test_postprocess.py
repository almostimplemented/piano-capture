import shutil

import numpy as np
import pytest
import soundfile as sf

from piano_capture.postprocess import process_wav_files

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")


@pytest.fixture
def recordings(tmp_path):
    def make(num_channels):
        audio_root = tmp_path / f"in{num_channels}"
        (audio_root / "2004").mkdir(parents=True)
        rng = np.random.default_rng(0)
        data = rng.uniform(-0.5, 0.5, size=(44100, num_channels)).astype("float32")
        sf.write(audio_root / "2004" / "a.wav", data, 44100, subtype="PCM_24")
        return audio_root

    return make


def test_mono_default_mixes_all_channels(tmp_path, recordings):
    audio_root = recordings(2)
    output_root = tmp_path / "out"

    process_wav_files(audio_root, output_root, sample_rate=16000, offset_ms=500)

    data, sample_rate = sf.read(output_root / "2004" / "a.wav")
    assert sample_rate == 16000
    assert data.ndim == 1
    assert len(data) == pytest.approx(8000, abs=16)
    assert np.abs(data).max() > 0.01


def test_mono_with_explicit_weights(tmp_path, recordings):
    audio_root = recordings(6)
    output_root = tmp_path / "out"

    process_wav_files(audio_root, output_root, channel_weights=[0, 0, 0.8, 0.8, 0.1, 0.1])

    data, _ = sf.read(output_root / "2004" / "a.wav")
    assert data.ndim == 1
    assert np.abs(data).max() > 0.01


def test_weights_for_missing_channels_are_rejected(tmp_path, recordings):
    # Previously this produced an all-silent file without any error
    audio_root = recordings(2)

    with pytest.raises(ValueError, match="has only 2 channel"):
        process_wav_files(audio_root, tmp_path / "out", channel_weights=[0, 0, 0.8, 0.8])


def test_stereo(tmp_path, recordings):
    audio_root = recordings(2)
    output_root = tmp_path / "out"

    process_wav_files(
        audio_root, output_root, stereo=True, stereo_c0_weights=[1, 0], stereo_c1_weights=[0, 1]
    )

    assert sf.info(str(output_root / "2004" / "a.wav")).channels == 2


def test_stereo_requires_both_weight_lists(tmp_path, recordings):
    with pytest.raises(ValueError, match="stereo_c1_weights"):
        process_wav_files(recordings(2), tmp_path / "out", stereo=True, stereo_c0_weights=[1])


def test_existing_outputs_are_skipped_unless_overwrite(tmp_path, recordings):
    audio_root = recordings(2)
    output = tmp_path / "out" / "2004" / "a.wav"
    output.parent.mkdir(parents=True)
    output.write_bytes(b"placeholder")

    process_wav_files(audio_root, tmp_path / "out")
    assert output.read_bytes() == b"placeholder"

    process_wav_files(audio_root, tmp_path / "out", overwrite=True)
    assert sf.info(str(output)).channels == 1
