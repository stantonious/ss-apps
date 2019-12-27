#!/bin/bash

source /home/pi/venvs/ss/bin/activate
gunicorn -t 180 -b 0.0.0.0:5006 hist_plot:app

