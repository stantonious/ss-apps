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
import os
from yamnet import yamnet as yamnet_model

parser = argparse.ArgumentParser(
    description='app used to record mel spectograms')

parser.add_argument('-a', '--archive-dir', default='/tmp', required=True)

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
            idxs = np.asarray(d['idxs'])
            infs= np.asarray(d['inferences'])
            mel=np.asarray(d['mel'])
            time=int(d['time'])
            sorted_idxs=np.argsort(idxs)
            infs = infs[sorted_idxs]
            
            #write infs/mel
            infs_fname = os.path.join(
                    args.archive_dir, '{}-infs.npy'.format(time))
            mel_fname = os.path.join(
                    args.archive_dir, '{}-mel.npy'.format(time))
            np.save(infs_fname,infs)
            np.save(mel_fname, mel)

        except Exception as e:
            print ('exception ', e)

    channel.basic_consume(queue=result.method.queue,
                          auto_ack=True,
                          on_message_callback=_callback)
    channel.start_consuming()
