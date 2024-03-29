import mido
import sounddevice as sd


def print_banner():
    print(
        """
 ________  ___  ________  ________   ________
|\\   __  \\|\\  \\|\\   __  \\|\\   ___  \\|\\   __  \\
\\ \\  \\|\\  \\ \\  \\ \\  \\|\\  \\ \\  \\\\ \\  \\ \\  \\|\\  \\
 \\ \\   ____\\ \\  \\ \\   __  \\ \\  \\\\ \\  \\ \\  \\\\\\  \\
  \\ \\  \\___|\\ \\  \\ \\  \\ \\  \\ \\  \\\\ \\  \\ \\  \\\\\\  \\
   \\ \\__\\    \\ \\__\\ \\__\\ \\__\\ \\__\\\\ \\__\\ \\_______\\
    \\|__|     \\|__|\\|__|\\|__|\\|__| \\|__|\\|_______|
 ________  ________  ________  _________  ___  ___  ________  _______
|\\   ____\\|\\   __  \\|\\   __  \\|\\___   ___\\\\  \\|\\  \\|\\   __  \\|\\  ___ \\
\\ \\  \\___|\\ \\  \\|\\  \\ \\  \\|\\  \\|___ \\  \\_\\ \\  \\\\\\  \\ \\  \\|\\  \\ \\   __/|
 \\ \\  \\    \\ \\   __  \\ \\   ____\\   \\ \\  \\ \\ \\  \\\\\\  \\ \\   _  _\\ \\  \\_|/__
  \\ \\  \\____\\ \\  \\ \\  \\ \\  \\___|    \\ \\  \\ \\ \\  \\\\\\  \\ \\  \\\\  \\\\ \\  \\_|\\ \\
   \\ \\_______\\ \\__\\ \\__\\ \\__\\        \\ \\__\\ \\ \\_______\\ \\__\\\\ _\\\\ \\_______\\
    \\|_______|\\|__|\\|__|\\|__|         \\|__|  \\|_______|\\|__|\\|__|\\|_______|"""
    )


if __name__ == "__main__":
    print("mido.get_output_names()")
    print(mido.get_output_names())
    print("sounddevice.query_devices()")
    print(sd.query_devices())
