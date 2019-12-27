#!/bin/bash
set -x 
set -e
branch=yamnet
sudo apt -y update

#install useful utils
sudo apt install -y vim bc git  python-pip python3-virtualenv python3-dev

tmp_folder=/tmp/dumping_ground
mkdir ${tmp_folder}
pushd ${tmp_folder}

#install seeed mic array
git clone https://github.com/respeaker/seeed-voicecard.git
pushd seeed-voicecard
sudo ./install.sh
popd 

#install system packages
sudo apt-get install -y openmpi-bin libopenmpi-dev libhdf5-dev portaudio19-dev python3-scipy llvm ffmpeg libblas3 liblapack3 liblapack-dev libblas-dev libatlas-base-dev

#install python env
mkdir ~/venvs
python3 /usr/lib/python3/dist-packages/virtualenv.py  --system-site-packages -p /usr/bin/python3 ~/venvs/ss
echo 'source ~/venvs/ss/bin/activate' >> ~/.bashrc
source ~/venvs/ss/bin/activate

# make ss env
sudo mkdir /var/log/ss && sudo chown pi:pi /var/log/ss
sudo mkdir -p /ss/archive/audio 
sudo mkdir -p /ss/archive/inference
sudo mkdir -p /ss/labels
sudo mkdir -p /ss/data
sudo chown pi:pi -R /ss

# get setup scripts
if [ ! -d "./ss-apps" ]; then
    git clone --single-branch --branch ${branch} https://github.com/stantonious/ss-apps.git
fi
pushd ss-apps
git checkout -b ${branch} && git pull -f origin ${branch}
popd

#install postgresql
if [ ! -d "/etc/postgresql/11" ]; then
    sudo apt-get install -y postgresql-11
    sudo su -u postgres createuser -s pi
    psql -c 'create database ss' postgres
    psql -f ss-apps/sql/ss_schema.sql ss
    psql -c "ALTER USER pi WITH PASSWORD 'raspberry';"
fi

#copy audio files
sudo cp ss-apps/setup/audio/*.wav /ss/data

# systemd setup
sudo cp ss-apps/setup/systemd/*.service /lib/systemd/system/
sudo cp ss-apps/setup/scripts/*.sh /usr/local/bin
sudo systemctl daemon-reload
#sudo systemctl enable ss-inf
sudo systemctl enable ss-yamnet-inf
sudo systemctl enable ss-led
sudo systemctl enable ss-heartbeat
#sudo systemctl enable ss-gui
#sudo systemctl enable ss-audioplayback

#pip packages
#TODO - Can any come in as system packages?
pip install pyaudio bokeh flask sqlalchemy pika gunicorn resampy psycopg2 pandas matplotlib

#install tensorflow lite
wget -O tf-get.sh https://raw.githubusercontent.com/PINTO0309/Tensorflow-bin/master/previous_versions/download_tensorflow-1.14.0-cp37-cp37m-linux_armv7l.sh
chmod +x tf-get.sh
./tf-get.sh
pip3 install tensorflow-1.14.0-cp37-cp37m-linux_armv7l.whl

#install rabbitmq
sudo curl -s https://packagecloud.io/install/repositories/rabbitmq/rabbitmq-server/script.deb.sh | sudo bash
sudo apt-get install -y rabbitmq-server
sudo systemctl enable rabbitmq-server

#get vggish pca/model
ss_dir=/opt/soundscene
vggish_dir=/opt/vggish
audioset_dir=/opt/audioset
sudo mkdir ${ss_dir}
sudo mkdir ${vggish_dir}
sudo mkdir ${audioset_dir}

#get yamnet model weights
sudo wget -O ${ss_dir}/yamnet.h5 https://storage.googleapis.com/audioset/yamnet.h5
sudo cp ss-apps/pi-core/yamnet/yamnet_class_map.csv ${ss_dir}


sudo curl -XGET -o ${vggish_dir}/vggish_pca_params.npz "https://storage.googleapis.com/audioset/vggish_pca_params.npz"
#wget -O ${vggish_dir}/ https://storage.googleapis.com/audioset/vggish_model.ckpt

#TODO - Install from clone above?
#install ss
declare -a pkgs=("pi-core" "pi-apps/leds" "pi-apps/br" "pi-apps/inf" "pi-apps/status" "pi-apps/debug" "pi-web/hist_plot" "pi-web/inf_gui" "pi-web/labeler" "pi-svc/audio_playback")
for i in "${pkgs[@]}"
do
	#pip install --upgrade --no-deps --force-reinstall git+https://git@github.com/stantonious/ss-apps.git@${branch}#subdirectory="${i}"
	pip install --upgrade --no-deps --force-reinstall git+https://git@github.com/stantonious/ss-apps.git@${branch}#subdirectory="${i}"
done


(crontab -l 2>/dev/null; echo "0 0 * * * find /ss/archive -type f -mtime +2 -delete") | crontab -

read -p "Would you like to install RaspiWifi? (y/N)" -n 1 -r -s
if [[ $REPLY =~ ^[Yy]$ ]]; then
	set +e
	# Install the awesome RaspiWifi
	raspi_dir=/usr/lib/raspbiwifi
	if [ ! -d "$raspi_dir" ]; then
	     git clone https://github.com/bryanstaley/RaspiWiFi.git
	     pushd RaspiWiFi
	     sudo python3 initial_setup.py
	     popd 
	fi
fi

#clean up
popd
sudo rm -rf ${tmp_folder}

echo 'please reboot!'


