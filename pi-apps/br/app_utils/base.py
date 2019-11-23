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
import pika
import numpy as np
import datetime
from yamnet import yamnet as yamnet_model

from business_rules import variables, actions, run_all, fields

ss_service_base_uri = 'https://services.soundscene.org/'

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
        import re
        import glob
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

    @staticmethod
    def _get_wav(t):
        import re
        import glob
        import io
        import gzip
        from subprocess import Popen, PIPE
        arch_dt = datetime.datetime.fromtimestamp(t)
        arch_dir = os.path.join(
            '/archive', str(arch_dt.year), str(arch_dt.timetuple().tm_yday))

        for _f in glob.glob(f'{arch_dir}/*.raw'):
            fname = os.path.basename(_f)
            m = re.match(
                r'(?P<timestamp>[^-]+)-(?P<duration>[^-]+)-(?P<rate>[^-]+)-(?P<channels>\d+).*', fname)
            ts = float(m.group('timestamp'))
            dur = int(m.group('duration'))
            channels = m.group('channels')
            rate = m.group('rate')
            f_start_dt = datetime.datetime.fromtimestamp(ts)
            f_end_dt = f_start_dt + datetime.timedelta(seconds=dur)

            if arch_dt >= f_start_dt and arch_dt < f_end_dt:
                with open(_f, 'rb') as arch_f:
                    # found the archive
                    wav_f = io.BytesIO()

                    popen_args = ['ffmpeg', '-f', 's16le', '-ac', str(channels), '-ar',
                                  str(rate), '-i', _f, '-f', 'mp3', 'pipe:1']

                    proc = Popen(popen_args, stdout=PIPE)

                    wav_f.write(proc.stdout.read())
                    wav_f.seek(0)
                    return wav_f
        return None



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
