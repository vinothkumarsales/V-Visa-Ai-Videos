#!/usr/bin/env bash
# usage: mix.sh video_silent.mp4 out.mp4   (needs voice.mp3, music.wav, sfx.wav)
set -e
V=${1:-video_silent.mp4}; OUT=${2:-final.mp4}
ffmpeg -y -loglevel error -i "$V" -i voice.mp3 -i music.wav -i sfx.wav -filter_complex "
[1:a]adelay=3000|3000,volume=1.0,aformat=sample_rates=44100:channel_layouts=stereo,asplit=2[vo][vsc];
[2:a]volume=0.32,aformat=sample_rates=44100:channel_layouts=stereo[mu];
[mu][vsc]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[mud];
[3:a]volume=0.8,aformat=sample_rates=44100:channel_layouts=stereo[fx];
[vo][mud][fx]amix=inputs=3:duration=longest:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=9,atrim=0:56.4[a]" \
 -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -t 56.4 "$OUT"
