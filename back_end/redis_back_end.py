#!/usr/bin/env python
"""
"""
import re
import redis
import numpy as np
import json
import time

from digital_rf_utils import *

r = redis.Redis(host='localhost', port=6379, db=0)
p = r.pubsub(ignore_subscribe_messages=True)


def drf_requests_handler(msg):
    print(f'got message: {msg}')

    channel = msg['channel'].decode()
    # get id for request from channel name
    req_id = re.findall(r'\d+', channel)[0] 
    if 'channels' in channel:
        # user is requesting channels from drf file
        drf_path = msg['data'].decode()
        drf_channels = get_drf_channels(drf_path)

        print(f'sending: responses:{req_id}:channels, {json.dumps(drf_channels)}')
        r.publish(f'responses:{req_id}:channels', json.dumps(drf_channels))
    elif 'data' in channel:
        req_params = json.loads(msg['data'])
        print(f'got request for data: {req_params} ')

        r.delete(f'responses:{req_id}:stream')
        try:
            spec_datas = read_digital_rf_data([req_params['drf_path']], plot_file=None, plot_type="spectrum", channel=req_params['channel'],
                subchan=0, sfreq=0.0, cfreq=None, atime=0,
                start_sample=int(req_params['start_sample']), stop_sample=int(req_params['stop_sample']), modulus=10000, integration=1, 
                zscale=(0, 0), bins=int(req_params['bins']), log_scale=False, detrend=False,msl_code_length=0,
                msl_baud_length=0)


            y_max = max([max(d['data']) for d in spec_datas['data']])
            y_min = min([min(d['data']) for d in spec_datas['data']])

            spec_datas['metadata']['y_max'] = y_max
            spec_datas['metadata']['y_min'] = y_min
            spec_datas['metadata']['n_samples']  = spec_datas['data'][0]['data'].shape[0]


            r.publish(f'responses:{req_id}:metadata', json.dumps(spec_datas['metadata']))


            print(f"going to send {len(spec_datas['data'])} data points")
            for i in range(len(spec_datas['data'])):
                d = spec_datas['data'][i]['data']
                r.xadd(f'responses:{req_id}:stream', {'data': json.dumps(d.tolist())}, maxlen=1000)
                if (i % 100 == 0):
                    print(f"Wrote to Redis: {i}")
                time.sleep(0.05)
            # send ending message
            r.xadd(f'responses:{req_id}:stream', {'data': json.dumps({'status': 'DONE'})}, maxlen=1000)
            print('Sent last message')
            




        except Exception as e:
            # output error message
            print(e)


def run_drf_stream():
    """Set ups a redis connection and updates data to the stream."""
    streamname = 'example'
    
    # subscribe to all requests from the front end
    p.psubscribe(**{'requests:*': drf_requests_handler})

    r.set('request-id', 0)

    while True:
        p.get_message()
        time.sleep(.01)
    




if __name__ == '__main__':
    run_drf_stream()
