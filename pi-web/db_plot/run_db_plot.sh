#!/bin/sh

export DB_PLOT_START='2021-01-14T00:00:00'
export DB_PLOT_END='2021-01-15T00:00:00'
export DB_PLOT_IDXS='0,35,38,39'
DIR=`dirname $0`
bokeh serve --allow-websocket-origin=${BOKEH_ALLOW_WS_ORIGIN} ${DIR}/../lib/python*/site-packages/db_plot/

