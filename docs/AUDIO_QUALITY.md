# Audio Quality Options

Audiovault gives you control over the format and bitrate of downloaded music via per-user preferences.

## Quality Tiers

| Setting | Format | Bitrate |
|---|---|---|
| `low` | MP3 | 128 kbps |
| `normal` | MP3 | 192 kbps |
| `high` | MP3 | 320 kbps |
| `best` | MP3 | 320 kbps |
| `lossless` | FLAC | lossless |

The default is `high` (320 kbps MP3) unless overridden in user preferences.

## How It Works

Quality is set per-user in preferences. When a download is queued:

1. The download manager reads `user.preferences["quality"]`
2. Maps it to the appropriate ffmpeg postprocessor (`FFmpegExtractAudio`)
3. yt-dlp fetches the best available source audio (`bestaudio/best`)
4. ffmpeg transcodes to the target format/bitrate

## Notes

- FLAC (`lossless`) is only as good as the source. If the source platform streams at 128/256 kbps AAC, the FLAC will be a lossless container of that lossy stream — not true lossless.
- MP3 320 kbps is transparent for most listeners and has the widest client compatibility.
- Format choice affects storage: a 4-minute track at 320 kbps MP3 ≈ 9 MB; FLAC ≈ 25–40 MB.
