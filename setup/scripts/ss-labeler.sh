#!/bin/bash

source /home/pi/venvs/ss/bin/activate
gunicorn labeler:app --reload -b :5006 -t 360