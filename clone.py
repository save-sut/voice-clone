"""สร้างเสียงพูดด้วยเสียงที่โคลนจากไฟล์ต้นแบบใน refs/

  .venv/bin/python clone.py --text "สวัสดีครับ"
  .venv/bin/python clone.py --file test-text.txt --takes 3
  .venv/bin/python clone.py --ref 15-reflect --text "..."     → ใช้ต้นแบบอื่น

ค่าเริ่มต้นมาจากการฟังเทียบ 2026-10-07: ต้นแบบ 13-chat-friend, 25 steps,
cfg 2.0 กับบรรทัดที่มีคำอังกฤษ และ 1.5 กับบรรทัดไทยล้วน (ฟังเป็นธรรมชาติกว่า)

ใช้โหมด Ultimate Cloning (ไฟล์เสียง + ข้อความที่พูดในไฟล์) ถ้ามี refs/<ชื่อ>.txt
ข้อความยาวให้แยกบรรทัดละ 1–2 ประโยค สคริปต์จะสร้างทีละบรรทัดแล้วต่อกัน (ยาวรวดเดียวจะเพี้ยน)
"""

import argparse
import re
import time
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).parent
DEFAULT_REF = "13-chat-friend"
CFG_THAI = 1.5  # ไทยล้วน
CFG_MIXED = 2.0  # มีคำอังกฤษ — ต่ำกว่านี้คำอังกฤษเริ่มไม่ชัด


def auto_cfg(line: str) -> float:
    return CFG_MIXED if re.search(r"[A-Za-z]", line) else CFG_THAI


def main() -> None:
    p = argparse.ArgumentParser(description="โคลนเสียงด้วย VoxCPM2")
    p.add_argument("--ref", default=DEFAULT_REF, help=f"ชื่อไฟล์ต้นแบบใน refs/ (ไม่ต้องใส่ .wav) ค่าเริ่มต้น {DEFAULT_REF}")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--text", help="ข้อความที่จะพูด")
    src.add_argument("--file", help="ไฟล์ข้อความ บรรทัดละ 1–2 ประโยค")
    p.add_argument("--takes", type=int, default=1, help="สร้างกี่แบบ (seed ต่างกัน) ไว้เลือกอันที่ดีสุด")
    p.add_argument("--cfg", type=float, help=f"สูง = ตามต้นแบบเคร่งขึ้น, ต่ำ = อิสระขึ้น (ไม่ใส่ = อัตโนมัติ {CFG_THAI}/{CFG_MIXED})")
    p.add_argument("--steps", type=int, default=25, help="จำนวน step (มาก = ละเอียดขึ้นแต่ช้าลง)")
    p.add_argument("--pause", type=float, default=0.35, help="ช่วงเงียบระหว่างบรรทัด (วินาที)")
    p.add_argument("--device", default="auto", help="auto / mps / cpu")
    p.add_argument("--timbre", help="ไฟล์เสียงแยกไว้จับโทนเสียง เช่น refs/mix/all.wav (ไม่ใส่ = ใช้ --ref)")
    p.add_argument("--tag", default="", help="คำต่อท้ายชื่อไฟล์ผลลัพธ์ ไว้แยกการทดลอง")
    p.add_argument("--style", help='สั่งอารมณ์/จังหวะ (ภาษาอังกฤษ) เช่น "cheerful, energetic, slightly faster"')
    p.add_argument("--no-prompt", action="store_true",
                   help="โหมด Controllable: ใช้แค่โทนเสียงจากต้นแบบ ไม่ลอกจังหวะการอ่าน (--style ได้ผลชัดขึ้น)")
    args = p.parse_args()

    ref_wav = ROOT / "refs" / f"{args.ref}.wav"
    ref_txt = ROOT / "refs" / f"{args.ref}.txt"
    if not ref_wav.exists():
        raise SystemExit(f"ไม่พบ {ref_wav} — อัดก่อนด้วย bash record.sh {args.ref}")
    prompt_text = ref_txt.read_text(encoding="utf-8").strip() if ref_txt.exists() else None
    if args.no_prompt:
        prompt_text = None
    elif args.style and prompt_text:
        # โหมด Ultimate ไม่รองรับคำสั่งในวงเล็บ — โมเดลจะอ่านคำสั่งออกมาเป็นเสียง (ทดสอบแล้ว 2026-10-07)
        raise SystemExit("--style ใช้ได้เฉพาะกับ --no-prompt (โหมด Ultimate จะอ่านคำสั่งออกมาเป็นเสียง)")
    elif not prompt_text:
        print(f"⚠️  ไม่มี {ref_txt.name} — ใช้โหมดโคลนจากเสียงอย่างเดียว (เหมือนน้อยกว่า Ultimate)")

    text = args.text if args.text else Path(args.file).read_text(encoding="utf-8")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    from voxcpm import VoxCPM  # import ช้า เลยไว้หลังเช็ก argument

    t0 = time.time()
    model = VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=False, optimize=False, device=args.device)
    sr = model.tts_model.sample_rate
    print(f"โหลดโมเดลเสร็จใน {time.time() - t0:.0f} วินาที (sample rate {sr})")

    timbre = ROOT / args.timbre if args.timbre else ref_wav
    if not timbre.exists():
        raise SystemExit(f"ไม่พบ {timbre}")
    clone_args = {"reference_wav_path": str(timbre)}
    if prompt_text:
        clone_args.update(prompt_wav_path=str(ref_wav), prompt_text=prompt_text)

    out_dir = ROOT / "out"
    out_dir.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    silence = np.zeros(int(sr * args.pause), dtype=np.float32)

    for take in range(1, args.takes + 1):
        seed = 1000 + take
        pieces = []
        t1 = time.time()
        for i, line in enumerate(lines, 1):
            cfg = args.cfg if args.cfg is not None else auto_cfg(line)
            print(f"[แบบ {take}/{args.takes}] บรรทัด {i}/{len(lines)} (cfg {cfg}): {line}")
            wav = model.generate(
                text=f"({args.style}){line}" if args.style else line,
                cfg_value=cfg,
                inference_timesteps=args.steps,
                seed=seed,
                **clone_args,
            )
            pieces += [np.asarray(wav, dtype=np.float32), silence]
        audio = np.concatenate(pieces[:-1])
        label = args.ref.replace("/", "_") + (f"-{args.tag}" if args.tag else "")
        out = out_dir / f"{stamp}-{label}-take{take}.wav"
        sf.write(out, audio, sr)
        print(f"✅ {out.relative_to(ROOT)} ({len(audio) / sr:.1f} วินาที, ใช้เวลา {time.time() - t1:.0f} วินาที)")


if __name__ == "__main__":
    main()
