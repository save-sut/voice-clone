#!/bin/bash
# ฟังเทียบ: เล่นเสียงต้นแบบ (เสียงจริง) แล้วตามด้วยเสียงที่โคลนได้ ทีละต้นแบบ
#   bash compare.sh                 → ทุกไฟล์ใน out/ (ไฟล์ล่าสุดของแต่ละต้นแบบ)
#   bash compare.sh 03-story        → เฉพาะต้นแบบที่ระบุ (ชุดเก่า: v1/03-story)
#   NOREF=1 bash compare.sh         → ฟังแต่เสียงที่โคลน ไม่เล่นต้นแบบ
set -euo pipefail
cd "$(dirname "$0")"

refs=("$@")
if [[ ${#refs[@]} -eq 0 ]]; then
  for w in refs/*.wav; do refs+=("$(basename "$w" .wav)"); done
fi

for r in "${refs[@]}"; do
  # ไฟล์ล่าสุดของต้นแบบนี้ (ชื่อไฟล์ขึ้นต้นด้วยเวลา จึงเรียงตามชื่อได้)
  label="${r//\//_}"   # v1/03-story → v1_03-story (ชื่อไฟล์ใน out/)
  out="$(ls out/*-"$label"-take*.wav 2>/dev/null | sort | tail -1 || true)"
  [[ -z "$out" ]] && { echo "— $r: ยังไม่มีไฟล์ใน out/"; continue; }
  echo
  echo "━━━ $r ━━━"
  if [[ -z "${NOREF:-}" ]]; then
    echo "🎙  เสียงจริง (ต้นแบบ)"
    afplay "refs/$r.wav"
    sleep 0.6
  fi
  echo "🤖 เสียงโคลน: $out"
  afplay "$out"
  read -r -p "ให้คะแนนในใจ 1–5 แล้วกด Enter เพื่อฟังต่อ... "
done
