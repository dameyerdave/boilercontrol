#!/bin/bash

DIR=$(dirname $0)

cd ${DIR}/..
nohup python -m http.server &
