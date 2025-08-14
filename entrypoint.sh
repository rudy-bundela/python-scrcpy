#!/bin/sh

ffmpeg -r 30 -f lavfi -i testsrc -vf scale=1280:960 -vcodec libx264 -profile:v baseline -pix_fmt yuv420p -f flv rtmp://localhost/live/test
adb connect 192.168.0.165:42667
scrcpy -ra.mp4 --video-codec=h264 --video-source=camera -b 5000000 --camera-high-speed --camera-size=1280x720 --video-buffer=250 --camera-fps=120 --no-playback --no-window --no-control --audio-codec=aac