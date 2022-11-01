from cgitb import text
from http.client import REQUESTED_RANGE_NOT_SATISFIABLE
import os
import requests
import json
from bs4 import BeautifulSoup
import math
from InquirerPy import inquirer
import xmltodict
import re
from tabulate import tabulate

h = {
    "Cache-Control": "no-cache",
    "Pragma": "no-cache"
}

def get_atis(airport):
    try:
        base_url = 'http://datis.clowd.io/api/'
        full_url = base_url + airport
        r = requests.get(full_url, headers=h)
        return json.loads(r.text)[0]['datis']
    except:
        return "ERROR: NO D-ATIS FOUND"

def get_latest_metar(airport, last_hours=2):
    base_url = 'https://www.aviationweather.gov/adds/dataserver_current/httpparam?'
    full_url = base_url
    params = {
        'dataSource' : 'metars',
        'requestType' : 'retrieve',
        'format' : 'xml',
        'mostRecent' : 'true',
        'stationString' : airport,
        'hoursBeforeNow' : last_hours
    }
    first = True
    for k, v in params.items():
        if first:
            full_url += '%s=%s' % (k, v)
            first = False
        else:
            full_url += '&%s=%s' % (k,v)
    r = requests.get(full_url, headers=h)
    print(full_url)
    soup = BeautifulSoup(r.text, features='xml')

    x = xmltodict.parse(r.text)
    metar_dict = x['response']['data']['METAR']
    return metar_dict

    #metars = soup.find_all('METAR')
    #metar_dicts = []
    #for m in metars:
    #    m_dict = {}
    #    for v in m.children:
    #        m_dict[v.name] = v.text
    #return soup.find('raw_text').text

def calc_wind_components(headwind_deg, wind_deg, wind_kts):
    alpha = wind_deg - headwind_deg 
    return (wind_kts * math.cos(math.radians(alpha)), wind_kts * math.sin(math.radians(alpha)))

def max_headwind(runway_components):
    max = -999
    max_rw = None
    for rw, (headwind, crosswind) in runway_components.items():
        if headwind > max:
            max = headwind
            max_rw = rw
    return rw

def sfo_runway_config(metar=None, print_table=True):
    wind_deg = 0
    wind_speed = 0
    runways = {
        '28' : 284.5,
        '10' : 104.5,
        '01' : 14.5,
        '19' : 194.5

    }
    wind_components = {}
    if metar:
        exp = re.compile(r'(?P<wind_deg>[0-9]{3})(?P<wind_spd>[0-9]{2})KT')
        m = exp.match(metar)
        wind_deg = int(m.group('wind_deg'))
        wind_speed = int(m.group('wind_spd'))
    else:
        metar = get_latest_metar('KSFO')
        wind_deg = int(metar['wind_dir_degrees'])
        wind_speed = int(metar['wind_speed_kt'])
    
    for rw, rw_deg in runways.items():
        wind_components[rw] = calc_wind_components(rw_deg, wind_deg, wind_speed)
    
    if print_table:
        table = []
        for k, v in wind_components.items():
            table.append([k, v[0], v[1]])
        print(tabulate(table, headers=['Runway', 'Headwind', 'Crosswind'], floatfmt='.0f'))

    if wind_speed < 10:
        return 'Norm Ops'
    else:
        if wind_components['01'][0] > -10 and abs(wind_components['01'][1]) < 20: 
            if wind_components['28'][0] > -10 and abs(wind_components['28'][1]) < 20:
                return 'Norm Ops'
            else:
                if wind_components['19'][0] > -10 and abs(wind_components['19'][1]) < 20 and wind_components['10'][0] > -10 and abs(wind_components['10'][1]):
                    return 'East Ops'
                else:
                    max_hw_rw = max_headwind(wind_components)
                    return 'Use Runway %s with headwind %d kts' % (max_hw_rw, wind_components[max_hw_rw][0])
        else:
            if wind_components['28'][0] > -10 and abs(wind_components['28'][1]) < 20:
                return 'West Ops'
            else:
                if wind_components['19'][0] > -10 and abs(wind_components['19'][1]) < 20 and wind_components['10'][0] > -10 and abs(wind_components['10'][1]):
                    return 'East Ops'
                else:
                    max_hw_rw = max_headwind(wind_components)
                    return 'Use Runway %s with headwind %d kts' % (max_hw_rw, wind_components[max_hw_rw][0])


if __name__ == '__main__':
    os.system('cls' if os.name == 'nt' else 'clear')

    while True:
        airport = inquirer.text(
            message = 'Airport:'
        ).execute()
        if len(airport) == 3:
            airport = 'k' + airport
        print(get_atis(airport.upper()), end='\n\n')
        print(get_latest_metar(airport.upper())['raw_text'], end='\n\n')
        #x = sfo_runway_config('25030KT')
        x = sfo_runway_config()
        print(x)