#!/bin/bash

source /home/pi/venvs/ss/bin/activate
backoff.py -p 10 -n 3 -e 3 -t 2 -c .5
