from setuptools import setup

setup(
    name="piano_capture",
    version="0.0.1",
    description="Data capture for Disklavier playback",
    url="",
    author="Andrew Edwards",
    author_email="a.c.edwards@qmul.ac.uk",
    license="None",
    packages=["piano_capture"],
    install_requires=["ffmpeg-python", "fire", "mido", "numpy", "python-rtmidi", "sounddevice", "soundfile", "tqdm"],
    zip_safe=False,
)
