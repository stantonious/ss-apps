#!/bin/sh

DIR=`dirname $0`

bokeh serve --allow-websocket-origin=192.168.1.34:5006 ${DIR}/../lib/python2.7/site-packages/rmq_app/

