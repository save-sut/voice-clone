#!/bin/bash
# อัดเสียงต้นแบบ → refs/<ชื่อ>.wav (48 kHz mono) + refs/<ชื่อ>.txt (ข้อความที่พูด)
#   bash record.sh 01-casual            → ใช้ไมค์ "MacBook Pro Microphone"
#   MIC="ชื่อไมค์" bash record.sh 01-casual
#   bash record.sh --list               → ดูรายชื่อไมค์
#   bash record.sh --test               → ทดสอบไมค์และห้อง (เสียงรบกวน + ระดับเสียง) ก่อนอัดจริง
# ถ้าชื่อตรงกับหัวข้อ "## <ชื่อ>" ใน sentences.md จะดึงประโยคมาเขียน .txt ให้เอง
set -euo pipefail
cd "$(dirname "$0")"

# อัดผ่าน rec.py (PortAudio) — ffmpeg avfoundation ทำเสียงหลุด ~11% บนเครื่องนี้ (ได้ยินเป็นเสียงจี่/จึ๊ด)
REC=(.venv/bin/python rec.py)

if [[ "${1:-}" == "--list" ]]; then
  "${REC[@]}" --list
  exit 0
fi

MIC="${MIC:-MacBook Pro Microphone}"

# ระดับเสียง: mean = ความดังเฉลี่ย, max = จุดที่ดังสุด (0 dB = เสียงแตก)
levels() {
  ffmpeg -nostdin -hide_banner -i "$1" -af volumedetect -f null - 2>&1 \
    | grep -oE "(mean|max)_volume: [-0-9.]+" | awk '{print $2}' | tr '\n' ' '
}

# เช็กระดับเสียงที่อัดได้ แล้วบอกว่าต้องแก้อะไร
judge() {
  local mean="$1" max="$2"
  awk -v m="$mean" -v x="$max" 'BEGIN {
    if (x > -1)       print "❌ เสียงแตก (ดังเกิน) — ถอยห่างไมค์อีกนิด หรือพูดเบาลง"
    else if (m < -32) print "❌ เบาเกินไป — ขยับเข้าใกล้ไมค์ (ประมาณ 1 ฝ่ามือ) หรือพูดดังขึ้น"
    else if (m < -28) print "⚠️  ค่อนข้างเบา — ขยับเข้าใกล้ไมค์อีกนิด"
    else              print "✅ ระดับเสียงดี"
  }'
}

# --test: อัดความเงียบ 3 วินาที (วัดเสียงรบกวนในห้อง) + พูด 5 วินาที (วัดระดับเสียงพูด)
if [[ "${1:-}" == "--test" ]]; then
  T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
  echo "🎙  ไมค์: $MIC"
  read -r -p "1) อยู่เงียบ ๆ 3 วินาที (วัดเสียงรบกวนในห้อง) — กด Enter เพื่อเริ่ม "
  "${REC[@]}" "$T/noise.wav" --device "$MIC" --seconds 3
  read -r -p "2) พูดอะไรก็ได้ด้วยเสียงปกติ 5 วินาที — กด Enter เพื่อเริ่ม "
  "${REC[@]}" "$T/speech.wav" --device "$MIC" --seconds 5
  read -r nmean _ <<<"$(levels "$T/noise.wav")"
  read -r smean smax <<<"$(levels "$T/speech.wav")"
  echo
  echo "เสียงรบกวนในห้อง: $nmean dB"
  echo "เสียงพูด: เฉลี่ย $smean dB, ดังสุด $smax dB"
  judge "$smean" "$smax"
  awk -v n="$nmean" -v s="$smean" 'BEGIN {
    snr = s - n
    printf "ความต่างเสียงพูดกับเสียงรบกวน (SNR): %.0f dB — ", snr
    if (snr >= 35)      print "✅ ดีมาก"
    else if (snr >= 25) print "⚠️  พอใช้ — ลองปิดแอร์/พัดลม หรือย้ายไปห้องที่เงียบกว่า"
    else                print "❌ เสียงรบกวนเยอะเกินไป — ต้องหาที่เงียบกว่านี้"
  }'
  echo "▶️  เล่นเสียงพูดที่อัดให้ฟัง..."
  afplay "$T/speech.wav"
  exit 0
fi

NAME="${1:?ใส่ชื่อไฟล์ด้วย เช่น bash record.sh 11-story-home}"
mkdir -p refs
RAW="$(mktemp -t vc-raw).wav"
trap 'rm -f "$RAW"' EXIT

# ดึงประโยคใต้หัวข้อ "## <ชื่อ> — ..." (บรรทัดแรกที่ไม่ว่าง)
TEXT="$(awk -v n="$NAME" '
  $0 ~ "^## " n "( |$)" { found=1; next }
  found && NF { print; exit }' sentences.md)"

# หัวข้อที่ขึ้นต้นด้วย "หัวข้อ:" = พูดสด ไม่มีบท → ไม่เขียน .txt ให้ (ต้องพิมพ์ตามที่พูดจริงเอง)
FREE=""
if [[ "$TEXT" == หัวข้อ:* ]]; then FREE=1; fi

echo "🎙  ไมค์: $MIC"
if [[ -n "$FREE" ]]; then
  echo "🗣  พูดสด ไม่ต้องอ่านบท ($TEXT)"
  echo "    พูดให้ได้ 15–20 วินาที เหมือนเล่าให้เพื่อนฟังจริง ๆ"
  echo
elif [[ -n "$TEXT" ]]; then
  echo "📄 อ่านประโยคนี้ (เล่าเหมือนคุยกับเพื่อน):"
  echo
  echo "    $TEXT"
  echo
fi
read -r -p "กด Enter เพื่อเริ่มอัด... "
for i in 3 2 1; do printf "%s.. " "$i"; sleep 1; done
echo "🔴 กำลังอัด — พูดได้เลย แล้วกด Enter เมื่อพูดจบ"

"${REC[@]}" "$RAW" --device "$MIC"   # หยุดเมื่อกด Enter

# ตัดช่วงเงียบหัว-ท้าย (เหลือไว้นิดหน่อย) → 48 kHz mono PCM16 ไม่ลด noise เพราะจะทำให้เสียงแบน
OUT="refs/$NAME.wav"
ffmpeg -nostdin -hide_banner -loglevel error -y -i "$RAW" \
  -af "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.15,areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.25,areverse" \
  -ar 48000 -ac 1 -c:a pcm_s16le "$OUT"

DUR="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT")"
printf "✅ บันทึก %s (%.1f วินาที)\n" "$OUT" "$DUR"
awk -v d="$DUR" 'BEGIN { if (d < 10) print "⚠️  สั้นไป — ควรยาว 12–20 วินาที"; else if (d > 25) print "⚠️  ยาวไป — ควรยาว 12–20 วินาที" }'
read -r MEAN MAX <<<"$(levels "$OUT")"
echo "ระดับเสียง: เฉลี่ย $MEAN dB, ดังสุด $MAX dB"
judge "$MEAN" "$MAX"

if [[ -n "$FREE" ]]; then
  rm -f "refs/$NAME.txt"
  echo "📝 พิมพ์สิ่งที่พูดลง refs/$NAME.txt ให้ตรงทุกคำ (ฟังซ้ำด้วย: afplay refs/$NAME.wav)"
elif [[ -n "$TEXT" ]]; then
  printf "%s\n" "$TEXT" > "refs/$NAME.txt"
  echo "📝 เขียน refs/$NAME.txt แล้ว — ถ้าพูดไม่ตรงทุกคำ ให้แก้ไฟล์นี้ให้ตรงกับที่พูดจริง"
elif [[ ! -f "refs/$NAME.txt" ]]; then
  echo "📝 อย่าลืมสร้าง refs/$NAME.txt ใส่ข้อความที่พูดในไฟล์เสียงนี้ให้ตรงทุกคำ"
fi

echo "▶️  เล่นเสียงที่อัดให้ฟัง..."
afplay "$OUT"
