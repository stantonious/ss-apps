A full set of software and tools to run the YAMNet (https://github.com/tensorflow/models/tree/master/research/audioset/yamnet) audio inference model on a Raspberry Pi 4b with SEEED 4 mic hat (https://wiki.seeedstudio.com/ReSpeaker_4_Mic_Array_for_Raspberry_Pi/)


To Setup

```
# Branch is either master or neosensory (for Buzz capability)
cd /tmp
wget https://raw.githubusercontent.com/stantonious/ss-apps/<branch>/setup/scripts/ss-setup.sh
chmod +x ss-setup.sh
./ss-setup.sh
```

To Install apps

`pip install git+https://git@github.com/stantonious/ss-apps.git#subdirectory="pi-core"`

`pip install git+https://git@github.com/stantonious/ss-apps.git#subdirectory="pi-apps/br"`

`pip install git+https://git@github.com/stantonious/ss-apps.git#subdirectory="pi-apps/inf"`

`pip install git+https://git@github.com/stantonious/ss-apps.git#subdirectory="pi-web/inf_gui"`

`pip install git+https://git@github.com/stantonious/ss-apps.git#subdirectory="pi-svc/audio_playback"`
