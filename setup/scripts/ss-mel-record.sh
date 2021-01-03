#!/bin/bash

source /home/pi/venvs/ss/bin/activate
mel_recorder.py --archive-dir=$1
