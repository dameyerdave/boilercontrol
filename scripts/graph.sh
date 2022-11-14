#!/usr/bin/env bash

DIR=$(dirname $0)

rrdtool graph ${DIR}/../tempweek.png \
  -s 'now - 24 hour' -e 'now' \
  DEF:oat=${DIR}/../temperature.rrd:oat:AVERAGE \
  LINE2:oat#00FF00:oat \
  DEF:boi_dg_o=${DIR}/../temperature.rrd:boi_dg_o:AVERAGE \
  LINE2:boi_dg_o#FF5E00:boi_dg_o \
  DEF:boi_dg_u=${DIR}/../temperature.rrd:boi_dg_u:AVERAGE \
  LINE2:boi_dg_u#0000FF:boi_dg_u \
  DEF:boi_ug_o=${DIR}/../temperature.rrd:boi_ug_o:AVERAGE \
  LINE2:boi_ug_o#580080:boi_ug_o \
  DEF:boi_ug_u=${DIR}/../temperature.rrd:boi_ug_u:AVERAGE \
  LINE2:boi_ug_u#00DBFF:boi_ug_u \
  DEF:solar=${DIR}/../temperature.rrd:solar:AVERAGE \
  LINE2:solar#FFE600:solar
