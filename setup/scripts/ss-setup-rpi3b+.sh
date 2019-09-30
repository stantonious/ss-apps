#!/bin/bash
set -x 
set -e

sudo apt-get update

#install useful utils
sudo apt-get install -y vim bc git  python-pip python3-virtualenv python3-dev

#install system packages
sudo apt-get install -y openmpi-bin libopenmpi-dev libhdf5-dev portaudio19-dev python-scipy llvm ffmpeg libblas3 liblapack3 liblapack-dev libblas-dev libatlas-base-dev

tmp_folder=/tmp/dumping_ground
mkdir ${tmp_folder}
pushd ${tmp_folder}

#install seeed mic array
git clone https://github.com/respeaker/seeed-voicecard.git
pushd seeed-voicecard
sudo ./install.sh
popd 

#install python env
mkdir ~/venvs && pushd ~/venvs
python3 /usr/lib/python3/dist-packages/virtualenv.py  --system-site-packages -p /usr/bin/python3 ss
echo 'source ~/venvs/ss/bin/activate' >> ~/.bashrc
source ~/venvs/ss/bin/activate
popd


# get setup scripts
git clone https://bitbucket.org/stantonious/ss-apps.git
# systemd setup
sudo cp ss-apps/setup/systemd/*.service /lib/systemd/system/
sudo cp ss-apps/setup/scripts/*.sh /usr/local/bin
sudo systemctl daemon-reload
sudo systemctl enable ss-inf
#sudo systemctl enable ss-gui
#sudo systemctl enable ss-audioplayback

#pip packages
#failure to install respampy pip install resampy 
#pip install pyaudio bokeh flask sqlalchemy pika gunicorn resampy==0.1.2
pip install pyaudio bokeh flask sqlalchemy pika gunicorn resampy

#install tensorflow lite
wget -O tensorflow-1.14.0-cp37-cp37m-linux_armv7l.whl https://github.com/PINTO0309/Tensorflow-bin/raw/master/tensorflow-1.14.0-cp37-cp37m-linux_armv7l.whl
pip3 install tensorflow-1.14.0-cp37-cp37m-linux_armv7l.whl 

#pulseaudio
#sudo apt-get install -y --only-upgrade alsa-utils
#sudo usermod -a -G audio pi

#install rabbitmq
sudo curl -s https://packagecloud.io/install/repositories/rabbitmq/rabbitmq-server/script.deb.sh | sudo bash
sudo apt-get install -y rabbitmq-server
sudo systemctl enable rabbitmq-server

#get vggish pca/model
ss_dir=/opt/soundscape
vggish_dir=/opt/vggish
audioset_dir=/opt/audioset
sudo mkdir ${ss_dir}
sudo mkdir ${vggish_dir}
sudo mkdir ${audioset_dir}

sudo curl -XGET -o ${vggish_dir}/vggish_pca_params.npz "https://storage.googleapis.com/audioset/vggish_pca_params.npz"
#wget -O ${vggish_dir}/ https://storage.googleapis.com/audioset/vggish_model.ckpt

#get soundsscape models
#sudo curl -XGET -o ${ss_dir}/soundscape.tflite "https://www.googleapis.com/storage/v1/b/ss-models/o/soundscape.tflite?alt=media"
sudo curl -XGET -o ${ss_dir}/1va-water.tflite "https://www.googleapis.com/storage/v1/b/ss-models/o/1va-water.tflite?alt=media"
sudo curl -XGET -o ${ss_dir}/1va-whistling.tflite "https://www.googleapis.com/storage/v:1/b/ss-models/o/1va-whistling.tflite?alt=media"
sudo curl -XGET -o ${ss_dir}/1va-music.tflite "https://www.googleapis.com/storage/v1/b/ss-models/o/1va-music.tflite?alt=media"
sudo curl -XGET -o ${ss_dir}/1va-dog.tflite "https://www.googleapis.com/storage/v1/b/ss-models/o/1va-dog.tflite?alt=media"
sudo curl -XGET -o ${ss_dir}/hio-nobaby.tflite "https://www.googleapis.com/storage/v1/b/ss-models/o/hio-nobaby.tflite?alt=media"
sudo rm  ${ss_dir}/soundscape.tflite
sudo ln -s  ${ss_dir}/hio-nobaby.tflite  ${ss_dir}/soundscape.tflite
sudo curl -XGET -o ${ss_dir}/vggish.tflite "https://www.googleapis.com/storage/v1/b/ss-models/o/vggish.tflite?alt=media"
sudo curl -XGET -o ${audioset_dir}/class_labels_indices.csv "http://storage.googleapis.com/us_audioset/youtube_corpus/v1/csv/class_labels_indices.csv"

#TODO - Install from clone above?
#install ss
declare -a pkgs=("pi-core" "pi-apps/br" "pi-apps/inf" "pi-web/inf_gui" "pi-svc/audio_playback")
for i in "${pkgs[@]}"
do
	pip install git+https://git@bitbucket.org/stantonious/ss-apps.git#subdirectory="${i}"
done

# make ss env
sudo mkdir /archive && sudo chown pi:pi /archive
(crontab -l 2>/dev/null; echo "0 0 * * * find /archive -type f -mtime +2 -delete") | crontab -

set +e
# Install the awesome RaspiWifi
raspi_dir=/usr/lib/raspbiwifi
if [ ! -d "$raspi_dir" ]; then
     git clone https://github.com/bryanstaley/RaspiWiFi.git
     pushd RaspiWiFi
     sudo python3 initial_setup.py
     popd 
fi

#clean up
popd
sudo rm -rf ${tmp_folder}

echo 'please reboot!'


