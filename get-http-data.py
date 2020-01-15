import requests
import json
import time
import datetime
import pickle
import multiprocessing
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
from influxdb import InfluxDBClient

# This posts creates a session from the create.asp and returns the session cookie
def bmc_login(ip,username,password): 
    payload = {
        'WEBVAR_USERNAME': username,
        'WEBVAR_PASSWORD': password
    }

    with requests.Session() as s:
        url = 'https://' + ip + '/rpc/WEBSES/create.asp'
        login = s.post(url, data=payload, verify=False)
        x = login.text
        session_cookie = x[1868:1903]
        return session_cookie

# This gets all sensor data from the web ui, and returns a list of dicts with SensorName, SensorReading, and RawReading
def get_all_sensors(ip, cookie, username):

    web_cookies = {
        'SessionCookie': cookie,
        'Username': username,
        'test':' 1', 
        'PNO': '4',
    }

    with requests.Session() as s:
        rec = s.get('https://' + ip + '/rpc/getallsensors.asp',  cookies = web_cookies, data="", verify=False)
        rec_text_trimmed = rec.text[1850:-44]
        rec_text_converted = rec_text_trimmed.replace('\'', '"')
        data_json = json.loads(rec_text_converted)
        for field in data_json:
            try:
                del field["SensorNumber"]
                del field["OwnerID"]
                del field["OwnerLUN"]
                del field["SensorType"]
                del field["SensorUnit1"]
                del field["SensorUnit2"]
                del field["SensorUnit3"]
                del field["AssertionEventMask"]
                del field["SensorAvailableState"]
                del field["SensorState"]            
                del field["DiscreteState"]
                del field["SettableThreshMask"]
                del field["LowNRThresh"]
                del field["LowCTThresh"]
                del field["LowNCThresh"]
                del field["HighNCThresh"]
                del field["HighCTThresh"]
                del field["HighNRThresh"]
                del field["SensorAccessibleFlags"]
            except:
                pass
        data_json.pop()
        #print(data_json)
        return data_json

def getCookies(host):
    try:
        with open(host + ".cookie", 'rb') as f:
            file_cookie = pickle.load(f)
            return file_cookie
            file.wrte("Got a cookie for IP: " + str(host))
    except:
        return ''

def writeCookies(host, session_cookie):
    with open(host + ".cookie", 'wb') as f:
        pickle.dump(session_cookie, f)

def GetSensorData(host):
    file = open("log.txt", "a")
    host['session_cookie'] = getCookies(host['ip'])
    if host.get('session_cookie') == "":
        session_cookie = bmc_login(host['ip'], host['username'], host['password'])
        host['session_cookie'] = session_cookie
        file.write("New session cookie for " + host['ip'] + " is: " + session_cookie + "\n")
    try:
        session_cookie = host['session_cookie']
        data = get_all_sensors(host['ip'], host['session_cookie'], host['username'])
    except:
        file.write("Was uable to get sensor information at" + str(time.time()))
        session_cookie = bmc_login(host['ip'], host['username'], host['password'])
        host['session_cookie'] = session_cookie
        file.write("New session cookie for " + host['ip'] + " is: " + session_cookie + "\n")
        data = get_all_sensors(host['ip'], host['session_cookie'], host['username'])
    client = InfluxDBClient(influx_host, 8086, influx_username, influx_password, influx_db)
    for measurements in data:
        json_body = [
        {
            "measurement": 'python-bmc',
            "tags": {
                "host": host['ip'],
                "source": "python-bmc",
                "sensor": measurements['SensorName']
            },
            "fields": {
                'SensorReading': measurements['SensorReading'],
                'RawReading':  measurements['RawReading']
                }
            }
        ]
        client.write_points(json_body, time_precision='ms')
    writeCookies(host['ip'], session_cookie)


########################### VARIABLES #########################################

remote_hosts = [
{"ip": "10.10.10.10", "username": "username_here", "password": "password_here", "session_cookie": "" }
]

influx_host = 'localhost'
influx_username = 'username_here'
influx_password = 'password_here'
influx_db = 'db_here'

########################### MAIN SCRIPT SECTION #########################################

if __name__ == "__main__":
    processes = [ ]
    for host in remote_hosts:
        t = multiprocessing.Process(target=GetSensorData, args=(host,))
        processes.append(t)
        t.start()
        time.sleep(5)
        t.join
