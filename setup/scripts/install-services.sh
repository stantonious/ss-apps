#!/bin/sh

source ~/venvs/ss/bin/activate

tmp_folder=/tmp/dumping_ground
mkdir ${tmp_folder}
pushd ${tmp_folder}

# get setup scripts
git clone https://bitbucket.org/stantonious/ss-apps.git
# systemd setup

#TODO - Install from clone above?
#install ss
declare -a pkgs=("pi-core" "pi-apps/br" "pi-apps/inf" "pi-web/inf_gui" "pi-svc/audio_playback")
for i in "${pkgs[@]}"
do
	pip install --force-reinstall --no-deps git+https://git@bitbucket.org/stantonious/ss-apps.git#subdirectory="${i}"
done
