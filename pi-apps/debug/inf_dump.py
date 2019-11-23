#!/home/pi/venvs/ss/bin/python3
""" inf dump app """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 2019"
__credits__ = []
__license__ = "GPL"

import pika
import numpy as np
import argparse
import time
import json
from yamnet import yamnet as yamnet_model

class_mapping = yamnet_model.class_names('/opt/soundscene/yamnet_class_map.csv')


parser = argparse.ArgumentParser(
    description='debug app used to display running inferences')

if __name__ == '__main__':
    args = parser.parse_args()

    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.exchange_declare(exchange='inference',
                             exchange_type='fanout')
    result = channel.queue_declare(queue='', exclusive=True)
    channel.queue_bind(queue=result.method.queue, exchange='inference')

    def _callback(ch, method, properties, body):
        try:
            d = json.loads(body)
            infs = list(zip(d['idxs'], d['inferences']))
            infs.sort(key=lambda x: x[1], reverse=True)

            infs = [f'{class_mapping[i]}({i}) -> {v} ' for i,v in infs]
            print (f'{d["time"]}' + '\n\t' +  '\n\t'.join(infs))

        except Exception as e:
            print ('exception ', e)

    channel.basic_consume(queue=result.method.queue,
                          auto_ack=True,
                          on_message_callback=_callback)
    channel.start_consuming()
