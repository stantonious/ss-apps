#!/bin/bash

source /home/pi/venvs/ss/bin/activate
export SS_API_KEY=TODO
play_audio.py -s 2 -e 2 -t 1 -c $2 -i $1 -f $3
