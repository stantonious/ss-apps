#!/bin/bash

source /home/pi/venvs/ss/bin/activate
smile.py --conf $2 --idx $1 --dump-dir $3
