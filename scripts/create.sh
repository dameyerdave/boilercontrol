#!/usr/bin/env bash

rrdtool create temperature.rrd -s 10 \
DS:oat:GAUGE:5m:-40:80 \
DS:boi_dg_o:GAUGE:5m:-40:80 \
DS:boi_dg_u:GAUGE:5m:-40:80 \
DS:boi_ug_o:GAUGE:5m:-40:80 \
DS:boi_ug_u:GAUGE:5m:-40:80 \
DS:solar:GAUGE:5m:-40:80 \
RRA:AVERAGE:0.5:1m:300h \
RRA:AVERAGE:0.5:5m:300h \
RRA:MIN:0.5:5m:300h \
RRA:MAX:0.5:5m:300h
