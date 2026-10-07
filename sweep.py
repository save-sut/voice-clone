"""ลองหลายค่าพร้อมกันเพื่อหาค่าที่เป็นธรรมชาติที่สุด (โหลดโมเดลครั้งเดียว)

  .venv/bin/python sweep.py --ref 03-story

ผลลัพธ์อยู่ที่ out/sweep-<เวลา>/ ชื่อไฟล์บอกค่าที่ใช้ ฟังเทียบด้วย:
  for f in out/sweep-*/*.wav; do echo "$f"; afplay "$f"; done
"""

import argparse
import time
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).parent

# ประโยคทดสอบ: ไทยล้วน / ไทยปนอังกฤษ (ตัวอังกฤษ) / ประโยคเดียวกันแต่เขียนคำอังกฤษเป็นคำอ่านไทย
LINES = {
    "thai": "เช้านี้รถติดมาก กว่าจะถึงที่ทำงานก็เกือบเก้าโมงครึ่งแล้ว",
    "eng": "ช่วยส่ง file presentation มาให้ผมทาง email ก่อนประชุมบ่ายสองด้วยนะครับ",
    "engthai": "ช่วยส่งไฟล์ พรีเซนเทชั่น มาให้ผมทางอีเมล ก่อนประชุมบ่ายสองด้วยนะครับ",
}

# (ชื่อ, cfg, steps, ใช้เสียงต้นแบบรวมจับโทนเสียงไหม)
VARIANTS = [
    ("base-cfg2.0-s10", 2.0, 10, False),  # ค่าเดิมที่ใช้รอบก่อน
    ("cfg1.5-s10", 1.5, 10, False),
    ("cfg2.5-s10", 2.5, 10, False),
    ("cfg2.0-s25", 2.0, 25, False),
    ("cfg1.5-s25", 1.5, 25, False),
    ("mix-cfg2.0-s25", 2.0, 25, True),
    ("mix-cfg1.5-s25", 1.5, 25, True),
]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--ref", default="03-story", help="ต้นแบบที่คุมจังหวะ/อารมณ์ (refs/<ชื่อ>.wav + .txt)")
    p.add_argument("--mix", default="refs/mix/all.wav", help="เสียงต้นแบบรวม ใช้จับโทนเสียง")
    args = p.parse_args()

    ref_wav = ROOT / "refs" / f"{args.ref}.wav"
    prompt_text = (ROOT / "refs" / f"{args.ref}.txt").read_text(encoding="utf-8").strip()
    mix_wav = ROOT / args.mix

    from voxcpm import VoxCPM

    model = VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=False, optimize=False, device="auto")
    sr = model.tts_model.sample_rate

    out_dir = ROOT / "out" / f"sweep-{time.strftime('%Y%m%d-%H%M%S')}"
    out_dir.mkdir(parents=True)
    t0 = time.time()
    for name, cfg, steps, use_mix in VARIANTS:
        if use_mix and not mix_wav.exists():
            print(f"ข้าม {name}: ไม่มี {mix_wav}")
            continue
        timbre = mix_wav if use_mix else ref_wav
        for key, text in LINES.items():
            wav = model.generate(
                text=text,
                prompt_wav_path=str(ref_wav),
                prompt_text=prompt_text,
                reference_wav_path=str(timbre),
                cfg_value=cfg,
                inference_timesteps=steps,
                seed=1001,
            )
            out = out_dir / f"{key}--{name}.wav"
            sf.write(out, np.asarray(wav, dtype=np.float32), sr)
            print(f"✅ {out.relative_to(ROOT)}  ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
