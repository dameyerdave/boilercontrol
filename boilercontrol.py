#!/usr/bin/env python

import RPi.GPIO as GPIO
from time import sleep
from datetime import datetime as dt
import yaml
import sys
import signal
import traceback
import click

sensor = {
    'outside_air_temp': "/sys/bus/w1/devices/28-0621c1b4fce2/w1_slave",
    'temp_boiler_dg_oben': "/sys/bus/w1/devices/28-0621c1cdcdda/w1_slave",
    'temp_boiler_dg_unten': "/sys/bus/w1/devices/28-0921c1043e9c/w1_slave",
    'temp_boiler_ug_oben': "/sys/bus/w1/devices/28-0821c109a808/w1_slave",
    'temp_boiler_ug_unten': "/sys/bus/w1/devices/28-0621c1abece9/w1_slave",
    'temp_solar': "/sys/bus/w1/devices/28-0821c0da11c5/w1_slave"
}

# Test cases
test = {
    'test1': {
        'now': '2330',
        'sensor': {
            'outside_air_temp': 20,
            'temp_boiler_dg_oben': 30,
            'temp_boiler_dg_unten': 30,
            'temp_boiler_ug_oben': 35,
            'temp_boiler_ug_unten': 25,
            'temp_solar': 55
        }
    },
    'test2': {
        'now': '2330',
        'sensor': {
            'outside_air_temp': 20,
            'temp_boiler_dg_oben': 49,
            'temp_boiler_dg_unten': 30,
            'temp_boiler_ug_oben': 35,
            'temp_boiler_ug_unten': 25,
            'temp_solar': 55
        }
    }
}

relais = {
    'boiler_dg': 5,
    'boiler_ug': 6,
    'electro_dg': 13,
    'electro_ug': 16,
    'valve': 19,
    'electro_aux': 20
}


def cleanup(signum=None, frame=None):
    print('GPIO cleanup.')
    GPIO.cleanup()
    sys.exit(0)


signal.signal(signal.SIGINT, cleanup)


def read_config():
    with open('boilercontrol.conf', 'r') as cf:
        try:
            return yaml.safe_load(cf)
        except Exception as ex:
            sys.exit(ex)


def read_manual():
    with open('manual.conf', 'r') as cf:
        try:
            return yaml.safe_load(cf)
        except Exception as ex:
            sys.exit(ex)


def to_time(val):
    val = str(val)
    return dt.strptime(val, '%H%M')


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
    return GPIO.LOW if val else GPIO.HIGH


def time_between(now, start, end):
    if end >= start:
        return now >= start and now <= end
    else:
        return now <= end or now >= start


GPIO.setmode(GPIO.BCM)
for rel, gpio in relais.items():
    print(f"Setup relais {rel} GPIO {gpio}...")
    GPIO.setup(gpio, GPIO.OUT, initial=GPIO.HIGH)


@click.command()
@click.option('--testcase', '-t', default=None)
def main(testcase=None):
    electro_dg_on = False
    electro_ug_on = False
    while True:
        manual = read_manual()
        config = read_config()
        try:
            # manual values
            electro_modus_dg = manual['dg']['electro']['modus']
            electro_modus_ug = manual['ug']['electro']['modus']

            # time values
            if testcase:
                now = to_time(test[testcase]['now'])
            else:
                now = dt.now()
            start_sol_ladung = to_time(config['time']['start_sol_ladung'])
            end_sol_ladung = to_time(config['time']['end_sol_ladung'])
            start_electro_ladung = to_time(
                config['time']['start_electro_ladung'])
            end_electro_ladung = to_time(config['time']['end_electro_ladung'])
            start_electro_aux = to_time(config['time']['start_electro_aux'])
            end_electro_aux = to_time(config['time']['end_electro_aux'])

            # temp configs
            temp_min_solar = config['temp']['min_solar']
            temp_diff_ein = config['temp']['diff_ein']
            temp_diff_aus = config['temp']['diff_aus']
            temp_min_electro = config['temp']['min_electro']
            temp_max_electro_dg = config['temp'][f"max_electro_{electro_modus_dg}"]
            temp_max_electro_ug = config['temp'][f"max_electro_{electro_modus_ug}"]
            temp_min_outside_air = config['temp']['min_outside_air']
            temp_solar_aux = config['temp']['solar_aux']

            # sensors
            if testcase:
                temp_solar = test[testcase]['sensor']['temp_solar']
                temp_boiler_dg_oben = test[testcase]['sensor']['temp_boiler_dg_oben']
                temp_boiler_dg_unten = test[testcase]['sensor']['temp_boiler_dg_unten']
                temp_boiler_ug_oben = test[testcase]['sensor']['temp_boiler_ug_oben']
                temp_boiler_ug_unten = test[testcase]['sensor']['temp_boiler_ug_unten']
                outside_air_temp = test[testcase]['sensor']['outside_air_temp']
            else:
                temp_solar = read_sensor('temp_solar')
                temp_boiler_dg_oben = read_sensor('temp_boiler_dg_oben')
                temp_boiler_dg_unten = read_sensor('temp_boiler_dg_unten')
                temp_boiler_ug_oben = read_sensor('temp_boiler_ug_oben')
                temp_boiler_ug_unten = read_sensor('temp_boiler_ug_unten')
                outside_air_temp = read_sensor('outside_air_temp')

            def boiler_on(_temp_oben, _temp_unten, _relais):
                _boiler_on = time_between(now, start_sol_ladung, end_sol_ladung) \
                    and temp_solar > temp_min_solar \
                    and temp_solar > _temp_oben + temp_diff_ein \
                    and (_temp_unten + temp_diff_aus - _temp_oben < 0
                         or _temp_unten + temp_diff_aus > _temp_oben)
                GPIO.output(relais[_relais], to_gpio(_boiler_on))
                return _boiler_on

            boiler_dg_on = boiler_on(
                temp_boiler_dg_oben, temp_boiler_dg_unten, 'boiler_dg')
            boiler_ug_on = boiler_on(
                temp_boiler_ug_oben, temp_boiler_ug_unten, 'boiler_ug')

            valve_open = boiler_dg_on or boiler_ug_on
            GPIO.output(relais['valve'], to_gpio(valve_open))

            def electro_on(_temp_unten, _temp_max, _running, _relais):
                _electro_on = time_between(now, start_electro_ladung, end_electro_ladung) \
                    and temp_solar <= temp_min_solar \
                    and (
                        _temp_unten < temp_min_electro and not _running
                        or _temp_unten < _temp_max and _running
                ) \

                GPIO.output(relais[_relais], to_gpio(_electro_on))
                return _electro_on

            electro_dg_on = electro_on(
                temp_boiler_dg_unten, temp_max_electro_dg, electro_dg_on, 'electro_dg')
            electro_ug_on = electro_on(
                temp_boiler_ug_unten, temp_max_electro_ug, electro_ug_on, 'electro_ug')

            electro_aux_on = time_between(now, start_electro_aux, end_electro_aux) \
                and outside_air_temp < temp_min_outside_air \
                and temp_solar < temp_solar_aux
            GPIO.output(relais['electro_aux'], to_gpio(electro_aux_on))

        except Exception as ex:
            print(f"Error: {ex}")
            traceback.print_exc()
        finally:
            sleep(60)

    cleanup()


if __name__ == '__main__':
    main()
