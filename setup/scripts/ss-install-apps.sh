#!/bin/sh

source ~/venvs/ss/bin/activate

tmp_folder=/tmp/dumping_ground
mkdir ${tmp_folder}
pushd ${tmp_folder}

# get setup scripts
git clone https://github.com/stantonious/ss-apps.git
# systemd setup
sudo cp ss-apps/setup/systemd/*.service /lib/systemd/system/
sudo cp ss-apps/setup/scripts/*.sh /usr/local/bin
sudo systemctl daemon-reload

#TODO - Install from clone above?
#install ss
declare -a pkgs=("pi-core" "pi-apps/br" "pi-apps/leds" "pi-apps/inf" "pi-apps/status" "pi-apps/debug" "pi-web/inf_gui" "pi-svc/audio_playback")
for i in "${pkgs[@]}"
do
	pip install --force-reinstall --no-deps git+https://git@github.com/stantonious/ss-apps.git#subdirectory="${i}"
done
