#!/bin/bash

source /home/pi/venvs/ss/bin/activate
buzz.py --idx=$1 --conf-threshold=$2 --pattern=$3 --hz=$4 --fps=$5 --buzz-max-intensity=$6


