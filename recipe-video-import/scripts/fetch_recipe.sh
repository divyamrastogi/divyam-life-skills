#!/usr/bin/env bash
# fetch_recipe.sh — Unified recipe content extractor
# Supports: YouTube, Instagram Reels, direct video URLs
# Usage: ./fetch_recipe.sh <url> [output_dir]
# Output: /tmp/recipe-import/ with transcript.txt, frames/, meta.json

set -e

URL="$1"
OUTDIR="${2:-/tmp/recipe-import}"

if [ -z "$URL" ]; then
  echo "Usage: $0 <url> [output_dir]"
  exit 1
fi

# Ensure tools
for cmd in yt-dlp ffmpeg whisper-cli; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "Installing $cmd..."
    if [ "$cmd" = "whisper-cli" ]; then
      brew install whisper-cpp
    else
      brew install "$cmd"
    fi
  fi
done

# Clean and create output dir
rm -rf "$OUTDIR"
mkdir -p "$OUTDIR/frames"

# ─────────────────────────────────────────────────────────────────────────────
# Detect source type
# ─────────────────────────────────────────────────────────────────────────────
SOURCE_TYPE="unknown"
if echo "$URL" | grep -qE '(youtube\.com/(watch|shorts)|youtu\.be/)'; then
  SOURCE_TYPE="youtube"
elif echo "$URL" | grep -qE 'instagram\.com/(reel|p)/'; then
  SOURCE_TYPE="instagram"
elif echo "$URL" | grep -qE '\.(mp4|mov|m4v|webm)'; then
  SOURCE_TYPE="direct"
else
  SOURCE_TYPE="other"
fi

echo "🔍 Detected source: $SOURCE_TYPE"
echo "🔗 URL: $URL"

# Save metadata
cat > "$OUTDIR/meta.json" <<METAEOF
{"source_type": "$SOURCE_TYPE", "url": "$URL", "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"}
METAEOF

# ─────────────────────────────────────────────────────────────────────────────
# YouTube pipeline — use existing fetch_captions.sh
# ─────────────────────────────────────────────────────────────────────────────
if [ "$SOURCE_TYPE" = "youtube" ]; then
  echo ""
  echo "📺 YouTube detected — using caption/description pipeline..."

  # Run existing YouTube caption fetcher
  CAPTIONS_DIR="$OUTDIR/yt-captions"
  bash ~/clawd/skills/youtube-recipe-import/scripts/fetch_captions.sh "$URL" "$CAPTIONS_DIR"

  # Find the output file
  VIDEO_ID=$(yt-dlp --get-id "$URL" 2>/dev/null || echo "unknown")
  CAPTION_FILE="$CAPTIONS_DIR/${VIDEO_ID}.txt"

  if [ -f "$CAPTION_FILE" ]; then
    cp "$CAPTION_FILE" "$OUTDIR/transcript.txt"
    echo "✅ Transcript ready: $OUTDIR/transcript.txt"
    
    # Check which source was used
    if [ -f "$CAPTION_FILE.meta" ]; then
      echo "   Source: $(cat "$CAPTION_FILE.meta")"
    fi
  else
    echo "❌ Failed to fetch YouTube content"
    exit 1
  fi

  # For YouTube Shorts, also try to extract frames (useful for on-screen text)
  # Download video (low quality is fine for frame extraction)
  echo ""
  echo "🎬 Downloading video for frame extraction..."
  yt-dlp -f "worst[ext=mp4]" -o "$OUTDIR/video.%(ext)s" "$URL" 2>/dev/null || \
  yt-dlp -o "$OUTDIR/video.%(ext)s" "$URL" 2>/dev/null || true

  if [ -f "$OUTDIR/video.mp4" ] || [ -f "$OUTDIR/video.webm" ]; then
    VIDEO_FILE=$(ls "$OUTDIR/video."* 2>/dev/null | head -1)
    DURATION=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$VIDEO_FILE" 2>/dev/null | cut -d. -f1 || echo "30")
    
    # Extract ~8-12 frames spread across the video (max 1 frame every 2 seconds)
    FPS=$(python3 -c "print(min(0.5, 10.0/max(int('$DURATION'),1)))" 2>/dev/null || echo "0.5")
    ffmpeg -i "$VIDEO_FILE" -vf "fps=$FPS" -q:v 3 "$OUTDIR/frames/frame_%03d.jpg" -y 2>/dev/null || true
    
    FRAME_COUNT=$(ls "$OUTDIR/frames/"*.jpg 2>/dev/null | wc -l | tr -d ' ')
    echo "📸 Extracted $FRAME_COUNT frames"
  fi

  echo ""
  echo "✅ YouTube import ready. Files:"
  echo "   Transcript: $OUTDIR/transcript.txt"
  echo "   Frames:     $OUTDIR/frames/ ($FRAME_COUNT files)"
  echo "   Meta:       $OUTDIR/meta.json"
  exit 0
fi

# ─────────────────────────────────────────────────────────────────────────────
# Instagram / Direct / Other — download video, Whisper transcribe, extract frames
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "📥 Downloading video..."

# Try yt-dlp first (works for Instagram public reels and direct URLs)
yt-dlp --no-check-certificates -o "$OUTDIR/video.%(ext)s" "$URL" 2>&1 || {
  echo "⚠️  yt-dlp download failed. Trying with different options..."
  yt-dlp --no-check-certificates --user-agent "Mozilla/5.0" -o "$OUTDIR/video.%(ext)s" "$URL" 2>&1 || {
    echo "❌ Could not download video. For Instagram, the reel may be private."
    echo "   Try browser fallback: open reel → snapshot → screenshot"
    exit 1
  }
}

VIDEO_FILE=$(ls "$OUTDIR/video."* 2>/dev/null | head -1)

if [ -z "$VIDEO_FILE" ]; then
  echo "❌ No video file downloaded"
  exit 1
fi

echo "✅ Downloaded: $VIDEO_FILE"

# ─────────────────────────────────────────────────────────────────────────────
# Extract audio → Whisper transcript
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "🎙️  Extracting audio and transcribing..."

AUDIO_WAV="$OUTDIR/audio.wav"
ffmpeg -i "$VIDEO_FILE" -ar 16000 -ac 1 -f wav "$AUDIO_WAV" -y 2>/dev/null

WHISPER_MODEL="${WHISPER_MODEL:-$HOME/.clawdbot/models/ggml-base.bin}"
if [ ! -f "$WHISPER_MODEL" ]; then
  echo "⚠️  Whisper model not found at $WHISPER_MODEL"
  echo "   Trying smaller model..."
  WHISPER_MODEL=$(find "$HOME/.clawdbot/models/" -name "*.bin" 2>/dev/null | head -1)
fi

if [ -f "$WHISPER_MODEL" ] && [ -f "$AUDIO_WAV" ]; then
  whisper-cli --model "$WHISPER_MODEL" --file "$AUDIO_WAV" --no-timestamps -otxt -of "$OUTDIR/transcript_raw" 2>/dev/null || true
  # whisper-cli outputs transcript_raw.txt
  if [ -f "$OUTDIR/transcript_raw.txt" ]; then
    cp "$OUTDIR/transcript_raw.txt" "$OUTDIR/transcript.txt"
    echo "✅ Transcript ready: $OUTDIR/transcript.txt"
  else
    echo "⚠️  Whisper transcription failed — will rely on frames only"
    touch "$OUTDIR/transcript.txt"
  fi
else
  echo "⚠️  No whisper model available — will rely on frames only"
  touch "$OUTDIR/transcript.txt"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Extract video frames at key moments
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "🎬 Extracting video frames..."

DURATION=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$VIDEO_FILE" 2>/dev/null | cut -d. -f1 || echo "30")

# Extract frames at ~0.5 fps (1 every 2 seconds), max ~15 frames
# This captures ingredient lists and step transitions in typical cooking reels
FPS=$(python3 -c "print(min(0.5, 15.0/max(int('$DURATION'),1)))" 2>/dev/null || echo "0.5")
ffmpeg -i "$VIDEO_FILE" -vf "fps=$FPS" -q:v 3 "$OUTDIR/frames/frame_%03d.jpg" -y 2>/dev/null || true

FRAME_COUNT=$(ls "$OUTDIR/frames/"*.jpg 2>/dev/null | wc -l | tr -d ' ')
echo "📸 Extracted $FRAME_COUNT frames"

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "✅ Import ready. Files in $OUTDIR/:"
echo "   Transcript: $OUTDIR/transcript.txt"
echo "   Frames:     $OUTDIR/frames/ ($FRAME_COUNT files)"
echo "   Video:      $VIDEO_FILE"
echo "   Meta:       $OUTDIR/meta.json"
echo ""
echo "Next: Analyze frames with image tool, parse transcript, generate SQL seed."
