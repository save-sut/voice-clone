"""อัดเสียงจากไมค์เป็น WAV 48 kHz mono PCM16 (ใช้แทน ffmpeg ที่ทำเสียงหลุดเป็นช่วง ๆ บน Mac)

  .venv/bin/python rec.py out.wav                  → อัดจนกว่าจะกด Enter
  .venv/bin/python rec.py out.wav --seconds 5      → อัด 5 วินาที
  .venv/bin/python rec.py --list                   → รายชื่อไมค์
"""

import argparse
import queue
import sys
import threading

import numpy as np
import sounddevice as sd
import soundfile as sf

SR = 48000


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("out", nargs="?")
    p.add_argument("--device", default="MacBook Pro Microphone")
    p.add_argument("--seconds", type=float, help="อัดตามเวลาที่กำหนด (ไม่ใส่ = อัดจนกด Enter)")
    p.add_argument("--list", action="store_true")
    args = p.parse_args()

    if args.list:
        for d in sd.query_devices():
            if d["max_input_channels"] > 0:
                print(d["name"])
        return
    if not args.out:
        sys.exit("ใส่ชื่อไฟล์ปลายทางด้วย")

    chunks: queue.Queue = queue.Queue()
    overflows = 0

    def callback(indata, frames, time_info, status):
        nonlocal overflows
        if status.input_overflow:
            overflows += 1
        chunks.put(indata[:, 0].copy())

    stop = threading.Event()
    with sd.InputStream(samplerate=SR, channels=1, dtype="float32", device=args.device,
                        blocksize=1024, latency="high", callback=callback):
        if args.seconds:
            stop.wait(args.seconds)
        else:
            sys.stdin.readline()

    audio = np.concatenate(list(chunks.queue)) if not chunks.empty() else np.zeros(0, np.float32)
    if args.seconds:
        audio = audio[: int(args.seconds * SR)]
    sf.write(args.out, audio, SR, subtype="PCM_16")
    if overflows:
        print(f"⚠️  เสียงหลุด {overflows} ครั้งระหว่างอัด — ปิดแอปที่หนัก ๆ แล้วอัดใหม่", file=sys.stderr)


if __name__ == "__main__":
    main()
