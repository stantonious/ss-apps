To Setup

```
branch=yamnet
cd /tmp
wget https://raw.githubusercontent.com/stantonious/ss-apps/${branch}/setup/scripts/ss-setup.sh
chmod +x ss-setup.sh
./ss-setup.sh
```

To Install apps

`pip install git+https://git@github.com/stantonious/ss-apps.git#subdirectory="pi-core"`

`pip install git+https://git@github.com/stantonious/ss-apps.git#subdirectory="pi-apps/br"`

`pip install git+https://git@github.com/stantonious/ss-apps.git#subdirectory="pi-apps/inf"`

`pip install git+https://git@github.com/stantonious/ss-apps.git#subdirectory="pi-web/inf_gui"`

`pip install git+https://git@github.com/stantonious/ss-apps.git#subdirectory="pi-svc/audio_playback"`
