#!/bin/bash
set -x 
set -e

if [ "$#" -ne 3 ]; then
    echo "Illegal number of parameters"
	exit 1
fi


key=$(curl -XGET "https://services.soundscene.org/soundscene/v.1.0/key/retrieve?user_id=$1&password=$2&device_id=$3" | sed -e 's/.\+"key": "\([^"]\+\)".*/\1/g')
sudo sed -i "s/TODO/$key/g" /usr/local/bin/ss-notification.sh
sudo sed -i "s/TODO/$key/g" /usr/local/bin/ss-emb-recorder.sh
sudo sed -i "s/TODO/$key/g" /usr/local/bin/ss-heartbeat.sh
