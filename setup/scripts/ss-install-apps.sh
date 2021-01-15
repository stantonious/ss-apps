#!/bin/bash
set -x 
set -e
branch=neosensory

source ~/venvs/ss/bin/activate

#install ss
declare -a pkgs=("pi-core" "pi-apps/image" "pi-apps/leds" "pi-apps/br" "pi-apps/inf" "pi-apps/status" "pi-apps/debug" "pi-web/neo_gui" "pi-web/hist_plot" "pi-web/inf_gui" "pi-web/labeler" "pi-svc/audio_playback")
for i in "${pkgs[@]}"
do
	pip install --upgrade --no-deps --force-reinstall git+https://git@github.com/stantonious/ss-apps.git@${branch}#subdirectory="${i}"
done

#install ss (with deps
declare -a pkgs=("pi-apps/neosensory")
for i in "${pkgs[@]}"
do
	pip install --upgrade --force-reinstall git+https://git@github.com/stantonious/ss-apps.git@${branch}#subdirectory="${i}"
done
