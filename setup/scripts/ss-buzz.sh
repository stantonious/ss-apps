#!/bin/bash

source /home/pi/venvs/ss/bin/activate
buzz.py --connection-attempts=10 --idx=$1


