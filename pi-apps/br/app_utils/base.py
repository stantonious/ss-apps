#!/usr/bin/python
'''
Created on Aug 28, 2019

@author: bstaley
'''
import argparse
import time
import json
import sys
import os
import pika
import numpy as np
from twilio.rest import Client
from business_rules import variables, actions, run_all, fields

ss_service_base_uri = 'https://mcm-dev-187021.appspot.com/'

import csv
class_mapping = {}
class_mapping_csv = csv.DictReader(
    open('/opt/audioset/class_labels_indices.csv'))
for _n in class_mapping_csv:
    class_mapping[int(_n['index'])] = _n['display_name']


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
