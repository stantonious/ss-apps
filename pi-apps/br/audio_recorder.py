#!/usr/bin/python
'''
Created on Aug 28, 2019

@author: bstaley
'''
import argparse
import time
import json
import sys
import pika
import numpy as np
from business_rules import variables, actions, run_all, fields

parser = argparse.ArgumentParser(
    description='record audio for provided inference')

parser.add_argument('-i', '--class-idx', type=int, required=True)
parser.add_argument('-n', '--notification-window', type=int, required=True)
parser.add_argument('-e', '--event-window', type=int, required=True)
parser.add_argument('-t', '--event-num-threshold', type=int, required=True)
parser.add_argument('-c', '--confidence-threshold', type=float, required=True)
parser.add_argument('-s', '--archive-size', type=int, default=10)


class Inference(object):
    def __init__(self, idx):
        self.last_conf = 0
        self.idx = idx
        self.cnt = 0
        self.act_expire = 0
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
    def act_expire(self):

        return self.act_expire

    @variables.numeric_rule_variable(label='window expire time')
    def win_expire(self):
        return self.win_expire

    @variables.numeric_rule_variable(label='action expire time')
    def time_to_action(self):
        return max([0, self.tracked_inference.act_expire - time.time()])

    @variables.numeric_rule_variable(label='window expire time')
    def time_to_window(self):
        return max([0, self.tracked_inference.win_expire - time.time()])


class InferenceActs(actions.BaseActions):

    def __init__(self, tracked_inference):
        self.tracked_inference = tracked_inference

    @actions.rule_action(params={'size': fields.FIELD_NUMERIC})
    def record_audio(self, size):
        connection = pika.BlockingConnection(
            pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        channel.queue_bind(queue='dump_commands', exchange='soundscene')

        print 'recording audio'
        d = dict(command='{}-{}-{}'.format(self.tracked_inference.idx,
                                           self.tracked_inference.last_conf,
                                           int(time.time())),
                 size=size)
        channel.basic_publish(exchange='soundscene',
                              routing_key='dump_commands',
                              body=json.dumps(d))

    @actions.rule_action(params={})
    def reset_cnt(self):
        print 'resetting cnt', self.tracked_inference.cnt
        self.tracked_inference.cnt = 0

    @actions.rule_action(params={'duration': fields.FIELD_NUMERIC})
    def reset_window(self, duration):
        self.tracked_inference.win_expire = time.time() + duration

    @actions.rule_action(params={'duration': fields.FIELD_NUMERIC})
    def reset_act_window(self, duration):
        print 'aw', time.time() + duration, time.time()
        self.tracked_inference.act_expire = time.time() + duration

    @actions.rule_action(params={})
    def inc_cnt(self):
        print 'cnt', self.tracked_inference.cnt + 1
        self.tracked_inference.cnt += 1


if __name__ == '__main__':
    args = parser.parse_args()

    class_idx = dict(name='idx',
                     operator='equal_to',
                     value=args.class_idx)
    cnt_exceeded = dict(name='cnt',
                        operator='greater_than',
                        value=args.event_num_threshold)
    inf_thresh = dict(name='last_conf',
                      operator='greater_than',
                      value=args.confidence_threshold)
    act_win = dict(name='time_to_action',
                   operator='equal_to',
                   value=0)
    window_elapased = dict(name='time_to_window',
                           operator='equal_to',
                           value=0)
    record_audio = dict(name='record_audio',
                        params=dict(size=args.archive_size))
    reset_act_win = dict(name='reset_act_window',
                         params=dict(duration=args.notification_window))
    reset_win = dict(name='reset_window',
                     params=dict(duration=args.event_window))
    reset_cnt = dict(name='reset_cnt',
                     params=dict())
    inc_cnt = dict(name='inc_cnt',
                   params=dict())
    rules = [
        {'conditions': {
            'all': [inf_thresh]
        },
            'actions':[inc_cnt]
        },
        {'conditions': {
            'all': [class_idx, cnt_exceeded, act_win]
        },
            'actions':[record_audio, reset_act_win, reset_cnt]
        },
        {'conditions': {
            'all': [window_elapased]
        },
            'actions':[reset_win, reset_cnt]
        }
    ]

    print 'br rules\n', json.dumps(rules)

    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.exchange_declare(exchange='inference',
                             exchange_type='fanout')
    result = channel.queue_declare(queue='', exclusive=True)
    channel.queue_bind(queue=result.method.queue, exchange='inference')

    inf = Inference(idx=args.class_idx)

    def _callback(ch, method, properties, body):
        try:
            d = json.loads(body)
            idx = np.argwhere(np.asarray(d['idxs']) == args.class_idx)
            if idx.shape[0] < 1:
                print 'no receiving inference for class idx', args.class_idx
                sys.exit()

            conf = d['inferences'][idx[0, 0]]

            inf.last_conf = conf

            run_all(rule_list=rules,
                    defined_variables=InferenceVars(inf),
                    defined_actions=InferenceActs(inf),
                    stop_on_first_trigger=False)

        except Exception as e:
            print 'exception ', e

    channel.basic_consume(queue=result.method.queue,
                          auto_ack=True,
                          on_message_callback=_callback)

    print ('Consuming!')
    channel.start_consuming()
