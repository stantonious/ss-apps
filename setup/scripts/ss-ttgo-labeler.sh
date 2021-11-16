#!/bin/bash

source /home/pi/venvs/ss/bin/activate
ttgo-labeler.py --h5-file=$1 --idx=$2 --conf=$3
