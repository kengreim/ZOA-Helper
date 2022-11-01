from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.utils import color_print
from tabulate import tabulate
import io
import csv
import os
import requests
from bs4 import BeautifulSoup
import webbrowser
import re
import json
import xmltodict
import math
import urllib

def simplify_dict(original_dict, new_dict_keys):
    return {k: v for k, v in original_dict.items() if k in new_dict_keys}

def load_airport_data(csv_filename):
    airport_data = {}
    with io.open(csv_filename,'r', encoding='utf8') as file:
        reader = csv.DictReader(file, delimiter=',')
        for row in reader:
            id = row['ident']
            airport_data[id] = row
    return airport_data

def load_airline_data(csv_filename):
    airline_data = {}
    with io.open(csv_filename,'r', encoding='utf8') as file:
        reader = csv.DictReader(file, delimiter=',')
        for row in reader:
            if row['ICAO'] != 'n\a':
                id = row['ICAO']
                airline_data[id] = row
    return airline_data

def load_route_data(csv_filename):
    route_data = []
    with io.open(csv_filename,'r', encoding='utf8') as file:
        reader = csv.DictReader(file, delimiter=',')
        for row in reader:
            route_data.append(row)
    return route_data

def load_aircraft_data(csv_filename):
    ac_data = {}
    with io.open(csv_filename,'r', encoding='utf8') as file:
        reader = csv.DictReader(file, delimiter=',')
        for row in reader:
            id = row['ICAO Code']
            if id != '' or id != 'n/a':
                ac_data[id] = row
    return ac_data

def load_FAA_route_data(csv_filename):
    route_data = {}
    with io.open(csv_filename,'r', encoding='utf8') as file:
        reader = csv.DictReader(file, delimiter=',')
        for row in reader:
            id = row['Orig']
            if id in route_data:
                route_data[id].append(row)
            else:
                route_data[id] = [row]
    return route_data

def load_alias_data(txt_filename):
    cmds = {}
    exp = re.compile(r'(?P<cmd>\.[a-zA-Z0-9]*) \.am rte (?P<txt>.+)')
    with io.open(txt_filename, 'r') as file:
        for line in file:
            m = exp.match(line)
            if m:
                cmds[m.group('cmd')] = m.group('txt').strip()
    return cmds

def sanitize_airport(airport):
    if len(airport) == 3:
        return 'K' + airport.upper()
    return airport.upper()

def flightaware_url(departure, arrival):
    base_url = 'https://flightaware.com/analysis/route.rvt?'
    params = {'origin': departure, 'destination': arrival}
    params_url = urllib.parse.urlencode(params)
    return base_url + params_url

def get_flightaware_routes(departure, arrival):
    r = requests.get(flightaware_url(departure,arrival))
    soup = BeautifulSoup(r.text, 'html.parser')
    table_raw = soup.find('table', class_ = 'prettyTable fullWidth')
    headers = [header.text for header in table_raw.find_all('th', class_ = 'secondaryHeader')]
    results = [{headers[i]: cell.text for i, cell in enumerate(row.find_all('td'))} for row in table_raw.find_all('tr')]
    return [simplify_dict(i, ['Frequency', 'Altitude', 'Full Route']) for i in results if i]

def open_flightaware(departure, arrival):
    webbrowser.open_new(flightaware_url(departure, arrival))

def open_skyvector(flightplan):
    url = 'https://skyvector.com/?fpl=%s' % flightplan
    webbrowser.open_new(url)

def get_faa_charts(airport, chart_type='SIDS'):
    chart_str_dict = {
        'SIDS'  : 'Departure Procedure (DP) Charts',
        'STARS' : 'Standard Terminal Arrival (STAR) Charts'
    }
    if chart_type not in chart_str_dict:
        return None
    chart_str = chart_str_dict[chart_type]
    
    url = 'https://nfdc.faa.gov/nfdcApps/services/ajv5/airportDisplay.jsp?airportId=%s' % airport
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    h3 = soup.find('h3', string=chart_str)
    if h3:
        spans = h3.find_next_siblings('span')
        results = {}
        for s in spans:
            links = s.find_all('a')
            for l in links:
                results[l.text] = l['href']
        return(results)
    else:
        return None

def get_atis(airport):
    h = {
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }
    try:
        base_url = 'http://datis.clowd.io/api/'
        full_url = base_url + airport
        r = requests.get(full_url, headers=h)
        return json.loads(r.text)[0]['datis']
    except:
        return 'ERROR: NO D-ATIS FOUND'

def get_latest_metar(airport, last_hours=2):
    h = {
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }
    try:
        base_url = 'https://www.aviationweather.gov/adds/dataserver_current/httpparam?'
        params = {
            'dataSource' : 'metars',
            'requestType' : 'retrieve',
            'format' : 'xml',
            'mostRecent' : 'true',
            'stationString' : airport,
            'hoursBeforeNow' : last_hours
        }
        params_url = urllib.parse.urlencode(params)
        full_url = base_url + params_url
        r = requests.get(full_url, headers=h)
        x = xmltodict.parse(r.text)
        metar_dict = x['response']['data']['METAR']
        return metar_dict
    except:
        return 'ERROR: METAR NOT FOUND OR UNAVAILABLE'

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

def main():
    # Load all necessary data
    airport_data = load_airport_data('data/airports.csv')
    airline_data = load_airline_data('data/airlines.csv')
    loa_route_data = load_route_data('data/routes.csv')
    aircraft_data = load_aircraft_data('data/aircraft.csv')
    faa_route_data = load_FAA_route_data('data/prefroutes_db.csv')
    alias_route_data = load_alias_data('data/ZOA_Alias.txt')
    
    # Create validator functions for InquirerPy
    def airport_validator(icao_code):
        return icao_code.upper() in airport_data
    def airline_validator(icao_code):
        return icao_code.upper() in airline_data
    def aircraft_validator(icao_code):
        return icao_code.upper() in aircraft_data

    # Prompt user to set default departure and arrival airports when the program starts.
    # Note that we don't call the validator functions here since we aren't actually performing
    # any lookups yet
    default_dep = ''
    default_arr = ''
    departure = inquirer.text(
        message = 'Default Departure:',
        default = default_dep
    ).execute()
    default_dep = sanitize_airport(departure)
    arrival = inquirer.text(
        message = 'Default Arrival:',
        default = default_arr
    ).execute()
    default_arr = sanitize_airport(arrival)
    if default_dep:
        try:
            color_print([('green', '\nD-ATIS')])
            print(get_atis(default_dep))
        except:
            print('ERROR: COULD NOT RETRIEVE D-ATIS')
        try:
            color_print([('green', '\nMETAR')])
            print(get_latest_metar(default_dep)['raw_text'])
        except:
            print('ERROR: COULD NOT RETRIEVE METAR')
    
    if default_dep == 'KSFO':
        color_print([('green', '\nRunway Winds and Config')])
        print(sfo_runway_config(print_table=True))

    while(True):
        print()
        action = inquirer.rawlist(
            message = 'Select an action:',
            choices = [
                'FlightAware IFR Analyzer',
                'SkyVector Analyzer',
                'ZOA Alias Routes',
                'FAA Preferred Routes',
                'LOA Route Check',
                'Chart Reference',
                'Code Lookup',
                'Clear Screen',
                'Exit'
            ],
            default = 'FlightAware IFR Analyzer',
            multiselect = False,
            show_cursor = False
        ).execute()

        if action == 'FlightAware IFR Analyzer':
            departure = inquirer.text(
                message = 'Departure:',
                validate = airport_validator,
                invalid_message = 'Airport not found',
                default = default_dep
            ).execute()
            arrival = inquirer.text(
                message = 'Arrival:',
                validate = airport_validator,
                invalid_message = 'Airport not found',
                default = default_arr
            ).execute()
            routes = get_flightaware_routes(departure, arrival)
            print(tabulate(routes, headers='keys'))
            open_browser = inquirer.confirm(
                message = 'Open in Browser?', 
                default = False
            ).execute()
            if open_browser:
                open_flightaware(departure, arrival)

        if action == 'SkyVector Analyzer':
            departure = inquirer.text(
                message = 'Departure:',
                validate = airport_validator,
                invalid_message = 'Airport not found',
                default = default_dep
            ).execute()
            arrival = inquirer.text(
                message = 'Arrival:',
                validate = airport_validator,
                invalid_message = 'Airport not found',
                default = default_arr
            ).execute()
            flightplan = inquirer.text(
                message = 'Flight Plan:',
            ).execute()
            full_plan = '%s %s %s' % (departure, flightplan, arrival)
            open_skyvector(full_plan)

        if action == 'ZOA Alias Routes':
            search_string = inquirer.text(
                message = 'Search String:',
                default = ''
            ).execute()
            results = [[k,v] for k, v in alias_route_data.items() if search_string.upper() in k.upper()]
            print(tabulate(results, headers=['Command', 'Text']))

        if action == 'FAA Preferred Routes':
            departure = inquirer.text(
                message = 'Departure:',
                validate = airport_validator,
                invalid_message = 'Airport not found',
                default = default_dep
            ).execute()
            arrival = inquirer.text(
                message = 'Arrival:',
                validate = airport_validator,
                invalid_message = 'Airport not found',
                default = default_arr
            ).execute()
            departure = departure.upper()[1:]
            arrival = arrival.upper()[1:]
            results = [i for i in faa_route_data[departure] if i['Dest'] == arrival]
            headers = ['Route String', 'Type', 'Altitude', 'Aircraft']
            print(tabulate([simplify_dict(i, headers) for i in results], headers='keys'))

        if action == 'LOA Route Check':
            departure = inquirer.text(
                message = 'Departure:',
                validate = airport_validator,
                invalid_message = 'Airport not found',
                default = default_dep
            ).execute()
            arrival = inquirer.text(
                message = 'Arrival:',
                validate = airport_validator,
                invalid_message = 'Airport not found',
                default = default_arr
            ).execute()
            results = [i for i in loa_route_data if re.match(i['Departure_Regex'], departure.upper()) and re.match(i['Arrival_Regex'], arrival.upper())]
            headers = ['Route', 'RNAV Required', 'Notes']
            print(tabulate([simplify_dict(i, headers) for i in results], headers='keys'))

        if action == 'Chart Reference':
            action2 = inquirer.rawlist(
                message = 'Select AirNav action:',
                choices = [
                'Open AirNav Airport Page',
                'SIDs',
                'STARs',
                'Skip'
            ],
            default = 'Open Airport Page',
            multiselect = False,
            show_cursor = False
            ).execute()

            if action2 == 'Open AirNav Airport Page':
                airport = inquirer.text(
                    message = '4-Letter ICAO:',
                    validate = airport_validator,
                    invalid_message = 'Airport not found'
                ).execute()
                url = 'https://www.airnav.com/airport/%s' % airport
                webbrowser.open_new(url)
            
            if action2 == 'STARs':
                airport = inquirer.text(
                    message = '4-Letter ICAO:',
                    validate = airport_validator,
                    invalid_message = 'Airport not found',
                    default = default_arr
                ).execute()
                stars = get_faa_charts(airport, 'STARS')
                if stars:
                    sorted_stars = sorted(stars.keys())
                    selected_star = inquirer.select(
                        message = 'Select STAR to Open',
                        choices = [Choice(value=None, name='Skip')] + sorted_stars,
                        default = None
                    ).execute()
                    if selected_star:
                        webbrowser.open_new(stars[selected_star])
                else:
                    color_print([('red', 'ERROR: STARs for %s not found' % airport)])

            if action2 == 'SIDs':
                airport = inquirer.text(
                    message = '4-Letter ICAO:',
                    validate = airport_validator,
                    invalid_message = 'Airport not found',
                    default = default_dep
                ).execute()
                sids = get_faa_charts(airport, 'SIDS')
                if sids:
                    sorted_sids = sorted(sids.keys())
                    selected_sid = inquirer.select(
                        message = 'Select SID to Open',
                        choices = [Choice(value=None, name='Skip')] + sorted_sids,
                        default = None
                    ).execute()
                    if selected_sid:
                        webbrowser.open_new(sids[selected_sid])
                else:
                    color_print([('red', 'ERROR: STARs for %s not found' % airport)])

            if action2 == 'Skip':
                pass

        if action == 'Code Lookup':
            action2 = inquirer.rawlist(
                message = 'Select a code:',
                choices = [
                'Airport Name Lookup',
                'Airline Callsign Lookup',
                'Aircraft Code Lookup',
                'Skip'
            ],
            default = 'Airport Name Lookup',
            multiselect = False,
            show_cursor = False
            ).execute()
            
            if action2 == 'Airport Name Lookup':
                airport = inquirer.text(
                    message = '4-Letter ICAO:',
                    validate = airport_validator,
                    invalid_message = 'Airport not found'
                ).execute()
                color_print([('green', airport_data[airport.upper()]['name'])])

            if action2 == 'Airline Callsign Lookup':
                airline = inquirer.text(
                    message = '3-Letter ICAO Prefix:',
                    validate = airline_validator,
                    invalid_message = 'Airline not found'
                ).execute()
                color_print([('green', airline_data[airline.upper()]['Call sign'])])
            
            if action2 == 'Aircraft Code Lookup':
                aircraft = inquirer.text(
                    message = '4-Letter ICAO Code:',
                    validate = aircraft_validator,
                    invalid_message = 'Aircraft not found'
                ).execute()
                color_print([('green', aircraft_data[aircraft.upper()]['Manufacturer and Aircraft Type / Model'])])
                color_print([('green', aircraft_data[aircraft.upper()]['WTC'])])
            
            if action2 == 'Skip':
                pass

        if action == 'Clear Screen':
            os.system('cls' if os.name == 'nt' else 'clear')
        
        if action == 'Exit':
            exit()

if __name__ == '__main__':
    # Clear screen if this was run directly from terminal
    os.system('cls' if os.name == 'nt' else 'clear')
    main()