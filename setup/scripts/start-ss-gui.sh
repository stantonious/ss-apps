#!/bin/bash

source /home/pi/venvs/ss/bin/activate
export BOKEH_ALLOW_WS_ORIGIN=home.soundscene.org:5006
run_inf_gui.sh
