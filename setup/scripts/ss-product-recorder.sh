#!/bin/bash

source /home/pi/venvs/ss/bin/activate
product_recorder.py  --archive-dir $1 --idx $2 --confidence $3 --product=mel inf emb