#!/bin/sh

DIR=`dirname $0`
bokeh serve --allow-websocket-origin=${BOKEH_ALLOW_WS_ORIGIN} ${DIR}/../lib/python*/site-packages/neo_gui/

