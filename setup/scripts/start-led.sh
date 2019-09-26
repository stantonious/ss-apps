#!/bin/bash

source /home/pi/venvs/ss/bin/activate
export SS_API_KEY=TODO
leds.py -s 120 -e 10 -t 2 -i $1 -c $2 -l $3 -C $4 
