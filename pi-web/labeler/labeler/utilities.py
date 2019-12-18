'''
Created on Dec 17, 2019

@author: bstaley
'''

import time,datetime
import numpy as np
import glob
import os
import re

def _get_audio_bytes(d,t,secs_prior=5.0,secs_aft=5.0,rate=16000.0,channels=2):
    raw_audio = np.full((0,channels),0,dtype=np.int16)
    last_ts=-1
    for _f in glob.glob(f'{d}/*.raw'):
        fname = os.path.basename(_f)
        m = re.match(
            r'(?P<timestamp>[^-]+)-(?P<duration>[^-]+)-(?P<rate>[^-]+)-(?P<channels>\d+).*', fname)
        if m is None:
            print ('no match',fname)
            continue
        ts = float(m.group('timestamp')) #end time
        dur = int(m.group('duration'))
        channels = int(m.group('channels'))
        frate = int(m.group('rate'))
        
        assert(ts >= last_ts)
        last_ts = ts
        assert (rate==frate)
    
        f_start_ut = ts - dur
        f_end_ut = ts
        
        req_start_ut = t - secs_prior
        req_end_ut = t + secs_aft
        
        if req_end_ut > f_start_ut and req_start_ut <= f_end_ut:
            data = np.fromfile(_f,dtype=np.int16).reshape(-1,channels)
            exact_duration = data.shape[0]/rate
            f_start_ut = ts-exact_duration #get exact file start
            
            rf_start_ut = max([f_start_ut,req_start_ut])
            rf_end_ut = min([f_end_ut,req_end_ut])
            
            d_start_idx = int((rf_start_ut-f_start_ut)*rate)
            d_end_idx=int((rf_end_ut-f_end_ut)*rate)
            audio_bytes=data[d_start_idx:d_end_idx,:]
            
            raw_audio=np.concatenate((raw_audio,audio_bytes))
    return raw_audio
        
def _get_wav(d,t,duration=10):
    import re
    import glob
    import io
    import gzip
    import tempfile
    from subprocess import Popen, PIPE
    
    channels=2
    rate=16000
    raw_audio = _get_audio_bytes(d=d, 
                                 t=t, 
                                 secs_prior=duration/2, 
                                 secs_aft=duration/2, 
                                 rate=16000, 
                                 channels=channels,)
    #write temp file
    temp_file='/tmp/.ss-audio.raw'
    with open(temp_file,'wb') as fp:
        raw_audio.tofile(fp,)
    wav_f = io.BytesIO()

    popen_args = ['ffmpeg', '-f', 's16le', '-ac', str(channels), '-ar',
                  str(rate), '-i', temp_file, '-f', 'mp3', 'pipe:1']

    proc = Popen(popen_args, stdout=PIPE)

    wav_f.write(proc.stdout.read())
    wav_f.seek(0)
    return wav_f
                