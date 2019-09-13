#!/bin/sh

DIR=`dirname $0`

gunicorn -b 0.0.0.0:5007 playback:app
