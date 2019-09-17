#!/bin/bash

source /home/pi/venvs/ss/bin/activate
export SS_API_KEY=TODO
notification.py -s 120 -e 10 -t 2 -c $2 -i $1
