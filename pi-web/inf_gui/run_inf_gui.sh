#!/bin/sh

DIR=`dirname $0`
export BOKEH_ALLOW_WS_ORIGIN=home.soundscene.org:5006

bokeh serve --allow-websocket-origin=192.168.1.34:5006 ${DIR}/../lib/python*/site-packages/inf_gui/

