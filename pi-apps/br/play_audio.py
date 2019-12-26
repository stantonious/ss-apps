#!/home/pi/venvs/ss/bin/python3
""" Notification App """
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
from app_utils import base
import numpy as np
from business_rules import variables, actions, run_all, fields

parser = argparse.ArgumentParser(
    description='send notification for provided inference')

parser.add_argument('-s', '--sleep-action-duration', type=int, required=True)
parser.add_argument('-e', '--event-window', type=int, required=True)
parser.add_argument('-t', '--event-num-threshold', type=int, required=True)
parser.add_argument('-c', '--confidence-threshold', type=float, required=True)
parser.add_argument('-i', '--index', type=int, required=True)
parser.add_argument('-f', '--audio-file', type=str, required=True)

audio_device_names=dict(
        default='bcm2835 ALSA',
        usb='USB2.0 Device')

class NotificationActs(base.InferenceActs):

    def __init__(self, tracked_inference):
        super().__init__(tracked_inference)

    @staticmethod
    def _get_audio_device_index(audio,dev_name):
        for _i in range(audio.get_device_count()):
            name=audio.get_device_info_by_index(_i)['name']
            print ('checking',name,dev_name)
            if dev_name in name:
                return _i
        return None

    @actions.rule_action(params={'audio_file': fields.FIELD_TEXT})
    def play_audio(self,
                  audio_file):
        import pyaudio
        import librosa
        
        chunk_size=1024
        
        audio = pyaudio.PyAudio()
        for _i in range(5):
            print('%s %s', _i, audio.get_device_info_by_index(_i)['name'])

        print ('opening')
        try:
            stream = audio.open(format=pyaudio.paFloat32,#audio.get_format_from_width(2),
                                channels=1, #TODO
                                rate=48000, #TOD)
                                output=True,
                                output_device_index=NotificationActs._get_audio_device_index(audio,audio_device_names['usb']),)
            print ('done opening')
        
            d, sr = librosa.load(audio_file,sr=16000)
            #resample
            d = librosa.resample(d,sr,48000)
            cnt=0

            while d.size > 0:
                data=d[:chunk_size]
                stream.write(data,data.shape[0])
                d=d[chunk_size:]
            print ('done playing')
        except Exception as e:
            print('exception',e)
        finally:
            if stream:stream.close()
            if audio:audio.terminate()


if __name__ == '__main__':
    args = parser.parse_args()

    tracked_idx = dict(name='idx',
                       operator='equal_to',
                       value=args.index)
    cnt_exceeded = dict(name='cnt',
                        operator='greater_than',
                        value=args.event_num_threshold)
    inf_thresh = dict(name='last_conf',
                      operator='greater_than',
                      value=args.confidence_threshold)

    play_audio = dict(name='play_audio',
                      params=dict(audio_file=args.audio_file))

    reset_act_win = dict(name='reset_act_window',
                         params=dict(duration=args.sleep_action_duration))
    reset_win = dict(name='reset_window',
                     params=dict(duration=args.event_window))

    rules = [
        {'conditions': {
            'all': [inf_thresh]
        },
            'actions':[base.inc_cnt]
        },
        {'conditions': {
            'all': [tracked_idx, cnt_exceeded, base.act_win]
        },
            'actions':[play_audio, reset_act_win, base.reset_cnt]
        },
        {'conditions': {
            'all': [base.window_elapsed]
        },
            'actions':[reset_win, base.reset_cnt]
        }
    ]

    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.exchange_declare(exchange='inference',
                             exchange_type='fanout')
    result = channel.queue_declare(queue='', exclusive=True)
    channel.queue_bind(queue=result.method.queue, exchange='inference')

    inf = base.Inference(idx=args.index)

    def _callback(ch, method, properties, body):
        try:
            d = json.loads(body)
            idx = np.argwhere(np.asarray(d['idxs']) == args.index)
            if idx.shape[0] < 1:
                return

            conf = d['inferences'][idx[0, 0]]

            inf.last_conf = conf
            inf.time = d['time']

            run_all(rule_list=rules,
                    defined_variables=base.InferenceVars(inf),
                    defined_actions=NotificationActs(inf),
                    stop_on_first_trigger=False)

        except Exception as e:
            print ('exception ', e)

    channel.basic_consume(queue=result.method.queue,
                          auto_ack=True,
                          on_message_callback=_callback)

    print ('Consuming!')
    channel.start_consuming()

