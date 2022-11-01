#!/usr/bin/env python

import RPi.GPIO as GPIO
from time import sleep
from datetime import datetime as dt, strptime
import yaml
import sys

sensor = {
    'outside_air_temp': "/sys/bus/w1/devices/28-0621c1b4fce2/w1_slave"
    'temp_boiler_dg_oben': "/sys/bus/w1/devices/28-0621c1cdcdda/w1_slave"
    'temp_boiler_dg_unten': "/sys/bus/w1/devices/28-0921c1043e9c/w1_slave"
    'temp_boiler_ug_oben': "/sys/bus/w1/devices/28-0821c109a808/w1_slave"
    'temp_boiler_ug_unten': "/sys/bus/w1/devices/28-0621c1abece9/w1_slave"
    'temp_solar': "/sys/bus/w1/devices/28-0821c0da11c5/w1_slave"
}

relais = {
    'boiler_dg': 5
    'boiler_ug': 6
    'electro_dg': 13
    'electro_ug': 16
    'valve': 19
    'electro_aux': 20
}

def read_config():
    with open('boilercontrol.conf', 'r') as cf:
        try:
            return yaml.safe_load(cf)
        except Exception as ex:
            sys.exit(ex)

def to_time(val):
    return strptime(val, '%H%M')

def read_sensor(name):
    value = "U"
    try:
        with open(sensor[name], 'r') as f:
            line = f.readline()
            if re.match(r"([0-9a-f]{2} ){9}: crc=[0-9a-f]{2} YES", line):
                line = f.readline()
                m = re.match(r"([0-9a-f]{2} ){9}t=([+-]?[0-9]+)", line)
                if m:
                    value = str(float(m.group(2)) / 1000.0)
    except IOError as ioe:
        print(f"Error reading sensor: {ioe}")
        raise
    return value

def to_gpio(val):
    GPIO.HIGH if val else GPIO.LOW

GPIO.setmode(GPIO.BOARD)
for rel in relais.values():
    GPIO.setup(rel, GPIO.LOW)
    
# GPIO.setup(relais['boiler_dg'], GPIO.LOW)
# GPIO.setup(relais['boiler_ug'], GPIO.LOW)
# GPIO.setup(relais['elector_dg'], GPIO.LOW)
# GPIO.setup(relais['electro_ug'], GPIO.LOW)
# GPIO.setup(relais['valve'], GPIO.LOW)
# GPIO.setup(relais['electro_aux'], GPIO.LOW)

electro_dg_on = False
electro_ug_on = False

while true:
    config = read_config()
    try:
        # time values
        now = dt.now()
        start_sol_ladung = to_time(config['time']['start_sol_ladung'])
        end_sol_ladung = to_time(config['time']['end_sol_ladung'])
        start_electro_ladung = to_time(config['time']['start_electro_ladung'])
        end_electro_ladung = to_time(config['time']['end_electro_ladung'])
        
        
        # temp configs
        temp_min_solar = config['temp']['min_solar']
        temp_diff = config['temp']['diff']
        temp_min_electro = config['temp']['min_electro']
        temp_max_electro = config['temp']['max_electro']
        temp_min_outside_air = config['temp']['min_outside_air']
        temp_solar_aux = config['temp']['solar_aux']
        
        # sensors
        temp_solar = read_sensor('temp_solar')
        temp_boiler_dg_oben = read_sensor('temp_boiler_dg_oben')
        temp_boiler_ug_oben = read_sensor('temp_boiler_ug_oben')
        outside_air_temp = read_sensor('outside_air_temp')
        
        def boiler_on(_temp, _relais):        
            _boiler_on = (now > start_sol_ladung \
                    or now < end_sol_ladung) \
                    and temp_solar > temp_min_solar \
                    and temp_solar > _temp + temp_diff 
            GPIO.output(relais[_relais], to_gpio(_boiler_on))
            return _boiler_on
        
        boiler_dg_on = boiler_on(temp_boiler_dg_oben, 'boiler_dg')
        boiler_ug_on = boiler_on(temp_boiler_ug_oben, 'boiler_ug')
        
        valve_open = boiler_dg_on or boiler_ug_on
        GPIO.output(relais['valve'], to_gpio(valve_open))
        
        
        def electro_on(_temp, _running, _relais):
            _electro_on = (now > start_electro_ladung \
                          or now < end_electro_ladung) \
                          and (
                                  _temp < temp_min_electro and !_running \
                                  or temp < temp_max_electro and _running
                              )
            GPIO.output(relais[_relais], to_gpio(_electro_on))
            return _electro_on
            
        electro_dg_on = electro_on(temp_boiler_dg_oben, electro_dg_on, 'electro_dg')
        electro_ug_on = electro_on(temp_boiler_ug_oben, electro_ug_on, 'electro_ug')
        
        electro_aux_on = (now > start_electro_aux \
                         or now < end_electro_aux) \
                         and outside_air_temp < temp_min_outside_air \
                         and temp_solar < temp_solar_aux
                         
        
    except Exception as ex:
        print(f"Error: {ex}")
    sleep(60)

GPIO.cleanup()










