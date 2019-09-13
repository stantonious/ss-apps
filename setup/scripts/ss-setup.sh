#!/bin/sh

#create ss user
# adduser --ingroup sudo ss

sudo apt-get update

#install system packages
sudo apt-get install -y openmpi-bin libopenmpi-dev libhdf5-dev portaudio19-dev python-scipy llvm ffmpeg libblas3 liblapack3 liblapack-dev libblas-dev

#install python env
#sudo apt-get install -y python-pip python-virtualenv
sudo apt-get install -y python-pip python3-virtualenv
mkdir ~/venvs && cd ~/venvs
#virtualenv --system-site-packages ss && source ~/venvs/ss/bin/activate
virtualenv  --system-site-packages -p /usr/bin/python3 ss

#
tmp_folder=/tmp/dumping_ground
mkdir ${tmp_folder}
pushd ${tmp_folder}

# get setup scripts
setup_scripts=ss-setup.tgz
curl --fail -o ${setup_scripts} -s "https://storage.googleapis.com/ss_packages/${setup_scripts}" && tar -xvf ./${setup_scripts}
# systemd setup
cp setup/scripts/*.sh ~/
sudo cp setup/systemd/*.service /lib/systemd/system/
sudo systemctl daemon-reload

#install tensorflow lite
#https://github.com/PINTO0309/Tensorflow-bin
#wget -O tensorflow-1.11.0-cp27-cp27mu-linux_armv7l.whl https://github.com/PINTO0309/Tensorflow-bin/raw/master/tensorflow-1.11.0-cp27-cp27mu-linux_armv7l_jemalloc.whl
#pip install tensorflow-1.11.0-cp27-cp27mu-linux_armv7l.whl
wget -O tensorflow-1.14.0-cp37-cp37m-linux_armv7l.whl https://github.com/PINTO0309/Tensorflow-bin/raw/master/tensorflow-1.14.0-cp37-cp37m-linux_armv7l.whl
pip3 install tensorflow-1.14.0-cp37-cp37m-linux_armv7l.whl 
#python 3.x
#wget -O tensorflow-1.13.1-cp35-cp35m-linux_armv7l.whl https://github.com/PINTO0309/Tensorflow-bin/raw/master/tensorflow-1.13.1-cp35-cp35m-linux_armv7l.whl
#pip install tensorflow-1.13.1-cp35-cp35m-linux_armv7l.whl

#pip packages
#failure to install respampy pip install resampy 
#pip install pyaudio bokeh flask sqlalchemy pika gunicorn resampy==0.1.2
pip install pyaudio bokeh flask sqlalchemy pika gunicorn resampy

#pulseaudio
#sudo apt-get install pulseaudio
#sudo systemctl --system enable pulseaudio
sudo apt-get -y upgrade alsa-utils
sudo usermod -a -G audio ss

#install seeed 4-mic array
pushd /tmp
sudo apt-get update
sudo apt-get upgrade
git clone https://github.com/respeaker/seeed-voicecard.git
cd seeed-voicecard
sudo ./install.sh
popd 

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
sudo curl -XGET -o ${ss_dir}/soundscape.tflite "https://www.googleapis.com/storage/v1/b/ss-models/o/soundscape.tflite?alt=media"
sudo curl -XGET -o ${ss_dir}/vggish.tflite "https://www.googleapis.com/storage/v1/b/ss-models/o/vggish.tflite?alt=media"
sudo curl -XGET -o ${audioset_dir}/class_labels_indices.csv "http://storage.googleapis.com/us_audioset/youtube_corpus/v1/csv/class_labels_indices.csv"

#install rabbitmq
sudo curl -s https://packagecloud.io/install/repositories/rabbitmq/rabbitmq-server/script.deb.sh | sudo bash
sudo apt-get install -y rabbitmq-server
sudo systemctl enable rabbitmq-server


#install ss
declare -a pkgs=("ss_infrastructure-1.0.tar.gz" "inf_app-1.0.tar.gz" "rmq_app-1.0.tar.gz" "playback_app-1.0.tar.gz")
for i in "${pkgs[@]}"
do
    curl -o ${i} -s "https://storage.googleapis.com/ss_packages/${i}" && pip install ${i}

done


#TODO add /lib/systemd/system/ss- start scripts

