#!/bin/sh

scrcpy -ra.mp4 --video-codec=h264 --video-source=camera -b 5000000 --camera-high-speed --camera-size=1280x720 --video-buffer=250 --camera-fps=120 --no-playback --no-window --no-control --audio-codec=aac