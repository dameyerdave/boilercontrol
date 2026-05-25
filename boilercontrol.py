#!/usr/bin/env python

import RPi.GPIO as GPIO
from time import sleep
from datetime import datetime as dt, timedelta as td, timezone as tz, date
import yaml
import sys
import signal
import traceback
import click
import re
import requests

def get_average_sun_power():
    now = dt.now()  # SolarEdge API expects UTC
    start = now - td(minutes=30)

    url = f"https://monitoringapi.solaredge.com/site/3809146/powerDetails"

    params = {
        "api_key": "W42ANY1ZV2D92JMZ4UVDOSFLD0B82NEF",
        "startTime": start.strftime("%Y-%m-%d %H:%M:%S"),
        "endTime": now.strftime("%Y-%m-%d %H:%M:%S"),
        "meters": "FeedIn"
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    meters = data["powerDetails"]["meters"]
    feed_in = next(m for m in meters if m["type"] == "FeedIn")

    values = [
        v["value"]
        for v in feed_in["values"]
        if v["value"] is not None
    ]

    if not values:
        return None

    return sum(values) / len(values)

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
    },
    'test3': {
        'now': '0300',
        'sensor': {
            'outside_air_temp': 3,
            'temp_boiler_dg_oben': 40,
            'temp_boiler_dg_unten': 30,
            'temp_boiler_ug_oben': 40,
            'temp_boiler_ug_unten': 30,
            'temp_solar': 35
        }
    },
    'test4': {
        'now': '0300',
        'sensor': {
            'outside_air_temp': 3,
            'temp_boiler_dg_oben': 40,
            'temp_boiler_dg_unten': 52,
            'temp_boiler_ug_oben': 40,
            'temp_boiler_ug_unten': 30,
            'temp_solar': 35
        }
    }
}

relais = {
    'boiler_dg': 5,
    'boiler_ug': 6,
    'electro_dg': 13,
    'electro_ug': 16,
    'valve': 19,
    'electro_aux': 20,
    'wp': 25,
    'boiler_atelier': 26
}

# digi_sensor = {
#     'pv_leistung': 23
# }

keep_on_until = {
    'wp': None,
    'boiler_atelier': None 
}

keep_off_until = {
    'wp': None,
    'boiler_atelier': None 
}

last_run_at = {
    'boiler_atelier': date(1970, 1, 1)
}

sun_power = {
    "next_run": dt.now(),
    "current_value": 0
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
    return dt.strptime(val, '%H%M').time()


def read_sensor(name: str, default: int = None):
    value = default
    try:
        with open(sensor[name], 'r') as f:
            line = f.readline()
            if re.match(r"([0-9a-f]{2} ){9}: crc=[0-9a-f]{2} YES", line):
                line = f.readline()
                m = re.match(r"([0-9a-f]{2} ){9}t=([+-]?[0-9]+)", line)
                if m:
                    value = float(m.group(2)) / 1000.0
    except IOError as ioe:
        print(f"Error reading sensor: {ioe}")
        if value == None:
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

# for rel, gpio in digi_sensor.items():
#     print(f"Setup digital sensor {rel} GPIO {gpio}...")
#     GPIO.setup(gpio, GPIO.IN)

@click.command()
@click.option('--testcase', '-t', default=None)
def main(testcase=None):
    electro_dg_on = False
    electro_ug_on = False
    boiler_dg_on = False
    boiler_ug_on = False
    boiler_dg_change_time = None
    boiler_ug_change_time = None
    while True:
        manual = read_manual()
        config = read_config()
        try:
            # manual values
            electro_modus_dg = manual['dg']['electro']['modus']
            electro_modus_ug = manual['ug']['electro']['modus']
            aux_enabled = manual['aux']['enabled']
            boiler_modus_atelier = manual['atelier']['boiler']['modus']
            wp_modus = manual['wp']['modus']

            # time values
            if testcase:
                now = to_time(test[testcase]['now'])
            else:
                now = to_time(dt.strftime(dt.now(), '%H%M'))
            start_sol_ladung = to_time(config['time']['start_sol_ladung'])
            end_sol_ladung = to_time(config['time']['end_sol_ladung'])
            start_electro_ladung = to_time(
                config['time']['start_electro_ladung'])
            end_electro_ladung = to_time(config['time']['end_electro_ladung'])
            start_electro_aux = to_time(config['time']['start_electro_aux'])
            end_electro_aux = to_time(config['time']['end_electro_aux'])
            time_hist_diff = config['time']['hyst_diff']

            # temp configs
            temp_min_solar = config['temp']['min_solar']
            temp_diff_ein = config['temp']['diff_ein']
            temp_diff_aus = config['temp']['diff_aus']
            temp_min_electro = config['temp']['min_electro']
            temp_max_electro_dg = config['temp'][f"max_electro_{electro_modus_dg}"]
            temp_max_electro_ug = config['temp'][f"max_electro_{electro_modus_ug}"]
            temp_min_outside_air = config['temp']['min_outside_air']
            temp_solar_aux = config['temp']['solar_aux']
            temp_hyst_diff = config['temp']['hyst_diff']

            # power configs
            power_min_wp = config['power']['min_wp']
            power_min_boiler_atelier = config['power']['min_boiler_atelier']


            # ontime configs
            ontime_wp = config['ontime']['wp']
            ontime_boiler_aterlier = config['ontime']['boiler_atelier']

            # onlock configs
            onlock_wp = config['onlock']['wp']

            # sensors
            if testcase:
                temp_solar = test[testcase]['sensor']['temp_solar']
                temp_boiler_dg_oben = test[testcase]['sensor']['temp_boiler_dg_oben']
                temp_boiler_dg_unten = test[testcase]['sensor']['temp_boiler_dg_unten']
                temp_boiler_ug_oben = test[testcase]['sensor']['temp_boiler_ug_oben']
                temp_boiler_ug_unten = test[testcase]['sensor']['temp_boiler_ug_unten']
                outside_air_temp = test[testcase]['sensor']['outside_air_temp']
            else:
                temp_solar = read_sensor('temp_solar', 0)
                temp_boiler_dg_oben = read_sensor('temp_boiler_dg_oben', 80)
                temp_boiler_dg_unten = read_sensor('temp_boiler_dg_unten', 80)
                temp_boiler_ug_oben = read_sensor('temp_boiler_ug_oben', 80)
                temp_boiler_ug_unten = read_sensor('temp_boiler_ug_unten', 80)
                outside_air_temp = read_sensor('outside_air_temp', 40)

            # digital sensors
            # pv_leistung = GPIO.input(digi_sensor['pv_leistung']) == 1

            def boiler_on(_temp_oben, _temp_unten, _relais, _running, _change_time):
                if _change_time is not None:
                    _minutes_since_change = (dt.now() - _change_time).total_seconds() / 60
                    if _minutes_since_change > time_hist_diff:
                        _change_time = None
                _boiler_on = time_between(now, start_sol_ladung, end_sol_ladung) \
                    and temp_solar > temp_min_solar \
                    and (
                            (_change_time is None and temp_solar > _temp_oben + temp_diff_ein) \
                        or  (_change_time is not None and temp_solar > _temp_oben + temp_diff_ein + temp_hyst_diff) \
                    ) \
                    and (
                            (_change_time is None and temp_solar > _temp_unten + temp_diff_aus) \
                        or  (_change_time is not None and temp_solar > _temp_unten + temp_diff_aus + temp_hyst_diff)
                    )
                if _running is not _boiler_on:
                    _change_time = dt.now()
                GPIO.output(relais[_relais], to_gpio(_boiler_on))
                return _boiler_on, _change_time

            boiler_dg_on, boiler_dg_change_time = boiler_on(
                temp_boiler_dg_oben, temp_boiler_dg_unten, 'boiler_dg', boiler_dg_on, boiler_dg_change_time)
            boiler_ug_on, boiler_ug_change_time = boiler_on(
                temp_boiler_ug_oben, temp_boiler_ug_unten, 'boiler_ug', boiler_ug_on, boiler_ug_change_time)
            

            valve_open = boiler_dg_on or boiler_ug_on
            GPIO.output(relais['valve'], to_gpio(valve_open))

            def electro_on(modus, _temp_unten, _temp_oben, _temp_max, _running, _relais):
                _electro_on = modus != 'aus' \
                    and time_between(now, start_electro_ladung, end_electro_ladung) \
                    and temp_solar <= temp_min_solar \
                    and (
                        _temp_unten < temp_min_electro and not _running
                        or _temp_oben < _temp_max and _running
                )

                GPIO.output(relais[_relais], to_gpio(_electro_on))
                return _electro_on

            electro_dg_on = electro_on(
                electro_modus_dg, temp_boiler_dg_unten, temp_boiler_dg_oben, temp_max_electro_dg, electro_dg_on, 'electro_dg')
            electro_ug_on = electro_on(
                electro_modus_ug, temp_boiler_ug_unten, temp_boiler_ug_oben, temp_max_electro_ug, electro_ug_on, 'electro_ug')

            electro_aux_on = time_between(now, start_electro_aux, end_electro_aux) \
                and outside_air_temp < temp_min_outside_air \
                and temp_solar < temp_solar_aux \
                and aux_enabled

            GPIO.output(relais['electro_aux'], to_gpio(electro_aux_on)) 
            
            if sun_power['next_run'] < dt.now():
                # Alle 12 Minuten daten von solaredge holen
                sun_power['next_run'] = dt.now() + td(minutes=12)
                sun_power['current_value'] = get_average_sun_power()

            average_sun_power = sun_power['current_value'] or 0
            print(f"Avarage sun power: {average_sun_power}")
            
            # Nur in AUTO modus
            now_dt = dt.now()
            
            print(f"WP modus: {wp_modus}")
            if wp_modus == 'auto':
                sun_ok = average_sun_power > power_min_wp

                # clear expired lock only
                if keep_off_until['wp'] is not None and now_dt >= keep_off_until['wp']:
                    keep_off_until['wp'] = None

                lock_active = keep_off_until['wp'] is not None

                # already running: run exactly until end time
                if keep_on_until['wp'] is not None:
                    wp_on = now_dt < keep_on_until['wp']

                    if not wp_on:
                        keep_on_until['wp'] = None
                        keep_off_until['wp'] = now_dt + td(hours=onlock_wp)

                # not running: start only if enough sun and no lock
                elif sun_ok and not lock_active:
                    wp_on = True
                    keep_on_until['wp'] = now_dt + td(hours=ontime_wp)

                else:
                    wp_on = False

            else:
                wp_on = wp_modus == 'ein'
                keep_on_until['wp'] = None
                keep_off_until['wp'] = None

            print(f"WP keep on until: {keep_on_until['wp']}")
            print(f"WP keep off until: {keep_off_until['wp']}")


            # AUTO modus Boiler
            print(f"Boiler modus: {boiler_modus_atelier}")
            if boiler_modus_atelier == 'auto':
                sun_ok = average_sun_power > power_min_boiler_atelier
                boiler_atelier_on = False

                if keep_on_until['boiler_atelier'] is not None:
                    boiler_atelier_on = now_dt < keep_on_until['boiler_atelier']

                    if not boiler_atelier_on:
                        keep_on_until['boiler_atelier'] = None

                elif sun_ok and last_run_at['boiler_atelier'] < now_dt.date():
                    boiler_atelier_on = True
                    keep_on_until['boiler_atelier'] = now_dt + td(hours=ontime_boiler_aterlier)
                    last_run_at['boiler_atelier'] = now_dt.date()

            else:
                boiler_atelier_on = boiler_modus_atelier == 'ein'
                keep_on_until['boiler_atelier'] = None

            print(f"Boiler keep on until: {keep_on_until['boiler_atelier']}")
            print(f"Boiler keep off until: {keep_off_until['boiler_atelier']}")
            
            GPIO.output(relais['wp'], to_gpio(wp_on))
            GPIO.output(relais['boiler_atelier'], to_gpio(boiler_atelier_on))
            
        except Exception as ex:
            print(f"Error: {ex}")
            traceback.print_exc()
        finally:
            sleep(60)

if __name__ == '__main__':
    
    main()
