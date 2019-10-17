#!/bin/bash

source /home/pi/venvs/ss/bin/activate
leds.py --num-leds 12 --idx 1 2 17 500 288 40 237 513 74 --conf .5 .5 .5 .6 .4 .7 .4 .4 .4 --color blue green yellow red LimeGreen purple white pink green
