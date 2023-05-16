from __future__ import annotations

import ffmpeg
import fire
import soundfile as sf

from pathlib import Path
from tqdm import tqdm

def process_wav_files(
    audio_root: str,
    output_root: str,
    sample_rate: int = 44100,
    offset_ms: int = 507,
    channel_weights: list[float] = [0, 0, 0.8, 0.8, 0.1, 0.1],
    stereo: bool = False,
    stereo_c0_weights: list[float] = None,
    stereo_c1_weights: list[float] = None,
    overwrite: bool = False,
):
    audio_root = Path(audio_root)
    output_root = Path(output_root)
    audio_paths = list(audio_root.rglob("*.wav"))
    offset_sec = offset_ms * 0.001

    # ffmpeg settings:
    if stereo:
        if (stereo_c0_weights is None) or (len(stereo_c0_weights) < 1):
            raise ValueError("Must specify weights for stereo_c0_weights")
        if (stereo_c1_weights is None) or (len(stereo_c1_weights) < 1):
            raise ValueError("Must specify weights for stereo_c0_weights")

        c0_expr = "+".join([f"{w}*c{idx}" for idx, w in enumerate(stereo_c0_weights)])
        c1_expr = "+".join([f"{w}*c{idx}" for idx, w in enumerate(stereo_c1_weights)])
        af_expr = f"pan=stereo|c0={c0_expr}|c1={c1_expr}"
    else:
        if (channel_weights is None) or (len(channel_weights < 1)):
            raise ValueError("Must specify weights for channel_weights")

        af_expr = "+".join([f"{w}*c{idx}" for idx, w in enumerate(channel_weights)])
        af_expr = f"pan=mono|c0={af_expr}"

    for p in (pbar := tqdm(audio_paths)):
        pbar.set_postfix_str(f"Processing: {p}")
        output_path = Path(output_root, p.relative_to(audio_root))

        if (not overwrite) and output_path.exists():
            pbar.set_postfix_str(f"Skipping: {p}")
            continue

        output_path.parent.mkdir(parents=True, exist_ok=True)

        (
            ffmpeg
            .input(str(p), ss=offset_sec)
            .output(str(output_path), af=af_expr, ar=sample_rate)
            .run(quiet=True, overwrite_output=True)
        )

if __name__ == "__main__":
    fire.Fire(process_wav_files)
