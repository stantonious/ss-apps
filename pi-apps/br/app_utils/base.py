#!/usr/bin/python
""" BR Base classes """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 2019"
__credits__ = []
__license__ = "GPL"

import argparse
import time
import json
import sys
import os
import glob
import re
import pika
import numpy as np
import datetime
from yamnet import yamnet as yamnet_model

from business_rules import variables, actions, run_all, fields

ss_service_base_uri = f'https://sound-scene.appspot.com/'
class_mapping = yamnet_model.class_names('/opt/soundscene/yamnet_class_map.csv')


class Inference(object):
    def __init__(self, idx):
        self.last_conf = 0
        self.idx = idx
        self.cnt = 0
        self.act_sleep_expire = 0
        self.win_expire = 0


class InferenceVars(variables.BaseVariables):

    def __init__(self, tracked_inference):
        self.tracked_inference = tracked_inference

    @variables.numeric_rule_variable(label='current confidence')
    def last_conf(self):
        return self.tracked_inference.last_conf

    @variables.numeric_rule_variable(label='idx')
    def idx(self):
        return self.tracked_inference.idx

    @variables.numeric_rule_variable(label='cnt')
    def cnt(self):
        return self.tracked_inference.cnt

    @variables.numeric_rule_variable(label='action expire time')
    def act_sleep_expire(self):
        return self.act_sleep_expire

    @variables.numeric_rule_variable(label='window expire time')
    def win_expire(self):
        return self.win_expire

    @variables.numeric_rule_variable(label='action expire time')
    def time_to_action(self):
        return max([0, self.tracked_inference.act_sleep_expire - time.time()])

    @variables.numeric_rule_variable(label='window expire time')
    def time_to_window(self):
        return max([0, self.tracked_inference.win_expire - time.time()])


class InferenceActs(actions.BaseActions):

    def __init__(self, tracked_inference):
        self.tracked_inference = tracked_inference

    @actions.rule_action(params={})
    def reset_cnt(self):
        self.tracked_inference.cnt = 0

    @actions.rule_action(params={'duration': fields.FIELD_NUMERIC})
    def reset_window(self, duration):
        self.tracked_inference.win_expire = time.time() + duration

    @actions.rule_action(params={'duration': fields.FIELD_NUMERIC})
    def reset_act_window(self, duration):
        self.tracked_inference.act_sleep_expire = time.time() + duration

    @actions.rule_action(params={})
    def inc_cnt(self):
        self.tracked_inference.cnt += 1

    @staticmethod
    def _get_embedding_file(embeddings):
        import io
        emb_f = io.BytesIO()
        np.save(emb_f, embeddings)
        emb_f.seek(0)
        return emb_f

    @staticmethod
    def _get_compressed_archive(t):
        import io
        import gzip
        arch_dt = datetime.datetime.fromtimestamp(t)
        arch_dir = os.path.join(
            '/archive', str(arch_dt.year), str(arch_dt.timetuple().tm_yday))

        for _f in glob.glob(f'{arch_dir}/*.raw'):
            fname = os.path.basename(_f)
            m = re.match(
                r'(?P<timestamp>[^-]+)-(?P<duration>[^-]+).*', fname)
            ts = float(m.group('timestamp'))
            dur = int(m.group('duration'))
            f_start_dt = datetime.datetime.fromtimestamp(ts)
            f_end_dt = f_start_dt + datetime.timedelta(seconds=dur)

            if arch_dt >= f_start_dt and arch_dt < f_end_dt:
                with open(_f, 'rb') as arch_f:
                    # found the archive
                    gzip_f = io.BytesIO()
                    with gzip.open(gzip_f, 'wb') as to_file:
                        to_file.write(arch_f.read())
                    gzip_f.seek(0)
                    return gzip_f
        return None

    #TODO - Combine this with impl from labeler.utilities
    @staticmethod
    def _get_audio_bytes(d,t,secs_prior=5.0,secs_aft=5.0,rate=16000.0,channels=2):
        raw_audio = np.full((0,channels),0,dtype=np.int16)
        last_ts=-1
        for _f in sorted(glob.glob(f'{d}/*.raw')):
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
        
            f_start_ut = ts
            f_end_ut = ts + dur
            
            req_start_ut = t - secs_prior
            req_end_ut = t + secs_aft
            
            if req_end_ut > f_start_ut and req_start_ut <= f_end_ut:
                data = np.fromfile(_f,dtype=np.int16).reshape(-1,channels)
                exact_duration = data.shape[0]/rate
                f_end_ut = ts+exact_duration #get exact file end
                
                rf_start_ut = max([f_start_ut,req_start_ut])
                rf_end_ut = min([f_end_ut,req_end_ut])
                
                d_start_idx = int((rf_start_ut-f_start_ut)*rate)
                d_end_idx=int((rf_end_ut-f_end_ut)*rate)
                if d_end_idx !=0:
                    audio_bytes=data[d_start_idx:d_end_idx,:]
                else:
                    audio_bytes=data[d_start_idx:,:]
                
                raw_audio=np.concatenate((raw_audio,audio_bytes))
        return raw_audio
    
    @staticmethod
    def _get_wav(d,
                 t,
                 duration=10,
                 rate=16000,
                 channels=2):
        import re
        import glob
        import io
        import gzip
        import tempfile
        from subprocess import Popen, PIPE
        
        raw_audio = InferenceActs._get_audio_bytes(d=d, 
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



# Default action wiring
reset_cnt = dict(name='reset_cnt',
                 params=dict())
inc_cnt = dict(name='inc_cnt',
               params=dict())

# Default condition wiring
act_win = dict(name='time_to_action',
               operator='equal_to',
               value=0)
window_elapsed = dict(name='time_to_window',
                      operator='equal_to',
                      value=0)
