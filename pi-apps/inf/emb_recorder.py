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

parser = argparse.ArgumentParser(
    description='app used to record yamnet embeddings')

parser.add_argument('-a', '--archive-dir', default='/tmp', required=True)
parser.add_argument('-i', '--idx', type=int, required=True)
parser.add_argument('-c', '--confidence', type=float, required=True)

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
            time=int(d['time'])
            idx = np.argwhere(idxs == args.idx)
            emb=np.asarray(d['embeddings'])

            conf = d['inferences'][idx[0, 0]]

            if conf > args.confidence:
                #write infs/mel
                emb_fname = os.path.join(args.archive_dir, str(idx[0,0]), '{}-emb.npy'.format(time))
                try:
                    np.save(emb_fname,emb)
                except FileNotFoundError:
                    print ("creating dir ",os.path.dirname(emb_fname));
                    os.mkdir(os.path.dirname(emb_fname))
                    np.save(emb_fname,emb)
        except Exception as e:
            print ('exception ', e)

    channel.basic_consume(queue=result.method.queue,
                          auto_ack=True,
                          on_message_callback=_callback)
    channel.start_consuming()
