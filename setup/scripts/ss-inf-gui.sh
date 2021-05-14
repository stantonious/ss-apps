#!/bin/bash

source /home/pi/venvs/ss/bin/activate
export INF_IDXS=0,35,38,39 #Speech, Whistling, Snoring, Gasp
export BOKEH_ALLOW_WS_ORIGIN=home.soundscene.org:5006
run_inf_gui.sh
