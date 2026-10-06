from __future__ import annotations

import fire
import shutil
import soundfile as sf
import subprocess

from pathlib import Path
from tqdm import tqdm


def _pan_expression(weights: list[float]) -> str:
    return "+".join([f"{w}*c{idx}" for idx, w in enumerate(weights)])


def process_wav_files(
    audio_root: str,
    output_root: str,
    sample_rate: int = 44100,
    offset_ms: int = 507,
    channel_weights: list[float] = None,
    stereo: bool = False,
    stereo_c0_weights: list[float] = None,
    stereo_c1_weights: list[float] = None,
    overwrite: bool = False,
):
    """Trim, mix down and resample captured recordings with ffmpeg.

    Every ".wav" file beneath audio_root is processed and written to the same
    relative path beneath output_root.

    Args:
        audio_root:
            Root directory of captured recordings.
        output_root:
            Root directory for processed files.
        sample_rate:
            Output sample rate.
        offset_ms:
            Amount trimmed from the start of each recording, to compensate for the
            delay between sending MIDI and the piano sounding.
        channel_weights:
            Mono mode: weight applied to each input channel (in order) before summing.
            Default is an equal-weight average of all channels. (The previous default,
            [0, 0, 0.8, 0.8, 0.1, 0.1], assumes a 6-channel recording.)
        stereo:
            Write stereo output using stereo_c0_weights and stereo_c1_weights instead
            of channel_weights.
        stereo_c0_weights:
            Stereo mode: per-input-channel weights for the left output channel.
        stereo_c1_weights:
            Stereo mode: per-input-channel weights for the right output channel.
        overwrite:
            Re-process files whose output already exists.
    """
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg was not found on PATH; please install it first")

    audio_root = Path(audio_root)
    output_root = Path(output_root)
    audio_paths = list(audio_root.rglob("*.wav"))
    offset_sec = offset_ms * 0.001

    if stereo:
        if (stereo_c0_weights is None) or (len(stereo_c0_weights) < 1):
            raise ValueError("Must specify weights for stereo_c0_weights")
        if (stereo_c1_weights is None) or (len(stereo_c1_weights) < 1):
            raise ValueError("Must specify weights for stereo_c1_weights")
        weight_lists = [stereo_c0_weights, stereo_c1_weights]
    else:
        if (channel_weights is not None) and (len(channel_weights) < 1):
            raise ValueError("Must specify weights for channel_weights")
        weight_lists = [channel_weights] if channel_weights is not None else []

    for p in (pbar := tqdm(audio_paths)):
        pbar.set_postfix_str(f"Processing: {p}")
        output_path = Path(output_root, p.relative_to(audio_root))

        if (not overwrite) and output_path.exists():
            pbar.set_postfix_str(f"Skipping: {p}")
            continue

        # ffmpeg silently treats weights for channels that don't exist as zero, which
        # can produce an all-silent output, so check them against the file.
        num_input_channels = sf.info(str(p)).channels
        for weights in weight_lists:
            if len(weights) > num_input_channels:
                raise ValueError(
                    f"{len(weights)} channel weights were given but {p} has only "
                    f"{num_input_channels} channel(s)"
                )

        # ffmpeg settings:
        if stereo:
            c0_expr = _pan_expression(stereo_c0_weights)
            c1_expr = _pan_expression(stereo_c1_weights)
            af_expr = f"pan=stereo|c0={c0_expr}|c1={c1_expr}"
        else:
            weights = channel_weights
            if weights is None:
                weights = [1 / num_input_channels] * num_input_channels
            af_expr = f"pan=mono|c0={_pan_expression(weights)}"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        command = [
            "ffmpeg",
            "-nostdin",
            "-y",
            "-ss", str(offset_sec),
            "-i", str(p),
            "-af", af_expr,
            "-ar", str(sample_rate),
            str(output_path),
        ]  # fmt: skip
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed on {p}:\n{result.stderr}")


def main():
    fire.Fire(process_wav_files, name="piano-capture-postprocess")


if __name__ == "__main__":
    main()
