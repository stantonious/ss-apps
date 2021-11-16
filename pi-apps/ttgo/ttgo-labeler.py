#!/home/pi/venvs/ss/bin/python3
""" inf dump app """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 2019"
__credits__ = []
__license__ = "GPL"

import sys
import pika
import numpy as np
import pickle
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from tensorflow import keras
import logging

import argparse
import time
import json

logger = logging.getLogger()
logger.setLevel(logging.INFO)

parser = argparse.ArgumentParser(description='TODO')
parser.add_argument('--h5-file',type=str,required=True)
parser.add_argument('--idx',type=int,required=True)
parser.add_argument('--conf',type=float,required=True)


id_to_name = {0:'bryan',
              1:'levi',
              2:'simon',
              3:'brayden',
              4:'alexa',
              5:'hikaru'}

def _get_pretty_name(for_idx,default='dunno'):
    if for_idx in id_to_name:
        return id_to_name[for_idx]
    return default

if __name__ == '__main__':
    args = parser.parse_args()

    with open(args.h5_file,'rb') as pf:
        model = keras.models.load_model(pf)


    ttgo_connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost'))
    ttgo_channel = ttgo_connection.channel()
    ttgo_channel.exchange_declare(exchange='ttgo',
                                  exchange_type='fanout'
                                  )
    
    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.exchange_declare(exchange='inference',
                             exchange_type='fanout')
    result = channel.queue_declare(queue='', exclusive=True)
    channel.queue_bind(queue=result.method.queue, exchange='inference')

    def _callback(ch, method, properties, body):
        global args
        global ttgo_channel
        global ttgo_connection
        try:
            d = json.loads(body)
            infs = list(zip(d['idxs'], d['inferences']))
            infs.sort(key=lambda x: x[1], reverse=True)

            print (infs[0])
            if infs[0][0] == args.idx and infs[0][1] > args.conf: #top inference is speech
                emb = np.asarray(d['embeddings'])
                print ('emb shape',emb.shape)

                r = model.predict(emb.reshape(1,-1))

                top_idx = np.argmax(r[0])
                payload=dict(type="label",
                             time=float(time.time()), 
                             idx=int(top_idx), 
                             pretty_name=_get_pretty_name(int(top_idx)),
                             conf=float(r[0][top_idx]))

                print ('sending ',payload,flush=True)
                ttgo_channel.basic_publish(exchange='ttgo',
                                           routing_key='',
                                           body=json.dumps(payload))

                print (f'class id:{r}')
        except pika.exceptions.AMQPError as sle:
            logger.exception('Reconnecting')
            ttgo_connection = pika.BlockingConnection(
                pika.ConnectionParameters('localhost'))
            ttgo_channel = ttgo_connection.channel()
            ttgo_channel.exchange_declare(exchange='ttgo',
                                          exchange_type='fanout'
                                          )
        except Exception as e:
            logger.exception('doh')
            raise e

    channel.basic_consume(queue=result.method.queue,
                          auto_ack=True,
                          on_message_callback=_callback)
    channel.start_consuming()
