#!/usr/bin/python
""" Heartbeat App """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 2019"
__credits__ = []
__license__ = "GPL"

import sys
import datetime,time
import requests

api_key = os.environ.get('SS_API_KEY')

ss_service_base_uri = 'https://services.soundscene.org/'

if __name__ == '__main__':
    
    url = f'{ss_service_base_uri}soundscene/v.1.0/device/add_status'
    
    if len(sys.argv) > 1:
        sleep_secs = int(sys.rgv[1])
    else:
        sleep_secs = 5 * 60 #5 mins
    
    print (f'Heartbeat every {sleep_secs}')
    
    while True:
        time.sleep(sleep_secs)
        
        params = dict(api_key=api_key,
                      status=0, #0 is good
                      at=time.time())
        r = requests.get(url=url,
                         verify=False, #TODO fix when GAE has an accredited CA
                         params=params)
        
        if r.status_code != 200:
            print (f'Unable to set device status:{r.status_code}')
        
        
        