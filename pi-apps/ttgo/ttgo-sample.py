#!/home/pi/venvs/ss/bin/python3

import argparse
import shutil
import os
import datetime
import re
import sys
import pika
import glob
import numpy as np
import json
import logging
import time
from enum import Enum
from yamnet import yamnet as yamnet_model


logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


ss_root='/ss'
ss_archive=os.path.join(ss_root,'archive')
ss_products=os.path.join(ss_archive,'products')
ss_labels=os.path.join(ss_root,'labels')

emb_pattern = re.compile(r'([\d]+)-(emb).npy')
class_mapping = yamnet_model.class_names('/opt/soundscene/yamnet_class_map.csv')

parser = argparse.ArgumentParser(
    description='send notification for provided inference')

parser.add_argument('--idx', type=int, required=True)
parser.add_argument('--conf-threshold', type=float, default=.8, required=False)
parser.add_argument('--emb-window', type=float, default=2., required=False)

def _find_files(for_idx=None,
                max_results=100,
                from_dt=None,
                to_dt=None):
    for_idx=for_idx or 0
    
    print ('indexing for idx:',for_idx)
    fs=[]

    for _f in sorted(glob.glob(ss_products+'/'+str(for_idx)+'/*-emb.npy')):
        if len(fs)>=max_results:break
        m=emb_pattern.match(os.path.basename(_f))
        if m is None:
            print ('regex miss!')
            continue
        
        dt=datetime.datetime.fromtimestamp(float(m.group(1)))
        if (from_dt and dt < from_dt) or (to_dt and dt > to_dt):
            continue

        print ('adding ',_f)
        fs.append(_f)
        
    return fs


if __name__ == "__main__":

    args = parser.parse_args()

    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost'))

    channel = connection.channel()
    channel.exchange_declare(exchange='inference',
                             exchange_type='fanout')
    channel.exchange_declare(exchange='ttgo-label',
                             exchange_type='fanout')
    channel.exchange_declare(exchange='ttgo',
                             exchange_type='fanout')
    channel.queue_declare(queue='infq', exclusive=True)
    channel.queue_bind(queue='infq', exchange='inference')
    channel.queue_declare(queue='labelq', exclusive=True)
    channel.queue_bind(queue='labelq', exchange='ttgo-label')

    logger.info('args:%s',args)

    idx_running_cnt = 0
    expire_sent = True;

    try:
        idx = int(args.idx)
    except:
        idx = np.where(class_mapping == _i)[0]

    def _label_callback(ch, method, properties, body):
        d = json.loads(body)
        print ('labeling!',d)
        label = d['class_label']
        sample_time = d['sample_time']

        if sample_time == 'now':
            sample_time = int(time.time())
        fs = _find_files(for_idx=0,
                         from_dt=datetime.datetime.fromtimestamp(sample_time-args.emb_window),
                         to_dt=datetime.datetime.fromtimestamp(sample_time+args.emb_window,))

        label_dir=os.path.join(ss_labels,label)

        if not os.path.exists(label_dir): 
            print (f'labeled dir:{label_dir} does not exist..creating')
            os.makedirs(label_dir)
        for _n in fs:
            print (f'labeling {_n} with {label}')
            dst_emb = os.path.join(label_dir,os.path.basename(_n))
            shutil.move(_n,dst_emb)

        expire_sent = True

    def _inf_callback(ch, method, properties, body):
        confidence = 0.
        global idx_running_cnt
        global expire_sent

        try:
            d = json.loads(body)
            d_idx = np.argwhere(np.asarray(d['idxs']) == idx)

            if d_idx.shape[0] >= 1: confidence = d['inferences'][d_idx[0,0]]

            if confidence > args.conf_threshold:
                idx_running_cnt += 1
                if idx_running_cnt > 4 or expire_sent:
                    idx_running_cnt = 0
                    expire_sent=False
                    channel.basic_publish(exchange='ttgo',
                                          routing_key='',
                                          body=json.dumps(dict(type="sample-req",
                                                               sample_time=int(time.time()),)))
            else:
                idx_running_cnt = 0
                if not expire_sent:
                    expire_sent = True
                    channel.basic_publish(exchange='ttgo',
                                          routing_key='',
                                          body=json.dumps(dict(type="sample-expire")))


        except pika.exceptions.AMQPError as sle:
            pass
        except Exception as e:
            logger.exception('doh')
            raise e
    
    channel.basic_consume(queue='infq',
                          auto_ack=True,
                          on_message_callback=_inf_callback)
    channel.basic_consume(queue='labelq',
                          auto_ack=True,
                          on_message_callback=_label_callback)

    logger.info('Consuming!')
    channel.start_consuming()


