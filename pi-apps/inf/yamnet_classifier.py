#!/home/pi/venvs/ss/bin/python3
""" Classifier App """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 2019"
__credits__ = []
__license__ = "GPL"

import numpy as np
import logging
import sys
import tensorflow as tf
import multiprocessing
import os
import json
import time
from threading import Thread
import pika
from inference import audio_archive_processor, audio_processor, framing_processor

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

# add file handler
fh = logging.FileHandler('/var/log/ss/ss.log')
fh.setLevel(logging.DEBUG)

RATE = 16000
# RATE = 48000
CHUNK = 1024
IDX = [0, 1, 2]
CHANNELS = 2
# CHANNELS = 1

AUD_ARCHIVE_SECONDS = 10

aud_rcv, aud_snd = multiprocessing.Pipe(False)
rec_rcv, rec_snd = multiprocessing.Pipe(False)
frm_rcv, frm_snd = multiprocessing.Pipe(False)
cmd_rcv, cmd_snd = multiprocessing.Pipe(False)
aud_cmd_rcv, aud_cmd_snd = multiprocessing.Pipe(False)


def dump_processor(cmd_snd):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.exchange_declare(exchange='soundscene'
                             )
    channel.queue_declare(queue='dump_commands',)
    channel.queue_bind(queue='dump_commands', exchange='soundscene')

    def _callback(ch, method, properties, body):
        d = json.loads(body)
        logger.info('sending dump:%s', body)
        cmd_snd.send(d)

    channel.basic_consume(queue='dump_commands',
                          auto_ack=True,
                          on_message_callback=_callback)
    channel.start_consuming()


def audio_control_processor(aud_cmd_snd=None):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='audio_control',)
    channel.queue_bind(queue='audio_control', exchange='soundscene')

    def _callback(ch, method, properties, body):
        d = json.loads(body)
        logger.info('sending audio control:%s', d)
        if aud_cmd_snd:
            if d['command'] == 'on':
                logger.info('turning on embeddings')
                aud_cmd_snd.send(0)
            elif d['command'] == 'off':
                logger.info('turning off embeddings')
                aud_cmd_snd.send(sys.maxint)
            elif d['command'] == 'resume_at':
                logger.info('resuming at', d['value'])
                aud_cmd_snd.send(d['value'])
            else:
                logger.info(
                    'received audio control command not understood:%s', d)

    channel.basic_consume(queue='audio_control',
                          auto_ack=True,
                          on_message_callback=_callback)

    channel.start_consuming()


def infer(frm_rcv):
    logger.info('infering ')
    from yamnet import yamnet as yamnet_model
    from yamnet import params
    import json
    
    top_k = 521 #report the top k classes
    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.exchange_declare(exchange='inference',
                             exchange_type='fanout'
                             )
    
    logger.info('model ')
    yamnet = yamnet_model.yamnet_frames_model(params)
    yamnet.load_weights('/opt/soundscene/yamnet.h5')
    logger.info('done model ')
    
    while True:
        try:
            aud_time, normalized_audio_1hz = frm_rcv.recv()
   
            if len(normalized_audio_1hz.shape) > 1:
                normalized_audio_1hz = np.mean(normalized_audio_1hz, axis=1)

            # returns [1,classes] classes=521
            scores, _ = yamnet.predict(np.reshape(normalized_audio_1hz, [1, -1]), steps=1)

            for _n in scores:#1 sec samples
                top_idxs = np.argsort(_n)[::-1][:top_k]
                inferences=_n[top_idxs]

                channel.basic_publish(exchange='inference',
                                                  routing_key='',
                                                  body=json.dumps(dict(time=aud_time,
                                                                       inferences=inferences.tolist(),
                                                                       mel=mel.tolist(),
                                                                       embeddings=[],#no embeddings produced for yamnet
                                                                       idxs=top_idxs.tolist())))
        except Exception as e:
            logger.exception(e)

def monitor_processes():
    aud_p = multiprocessing.Process(
        target=audio_processor.record_audio, args=(aud_snd,
                                                   rec_snd,  # None
                                                   RATE,
                                                   CHUNK,
                                                   IDX,
                                                   CHANNELS))
    aud_p.start()
    rec_p = multiprocessing.Process(
        target=audio_archive_processor.archive_audio, args=(rec_rcv,
                                                            RATE,
                                                            CHANNELS,
                                                            AUD_ARCHIVE_SECONDS,
                                                            '/archive'
                                                            ))

    rec_p.start()
    print ('starting frm')
    frm_p = multiprocessing.Process(
        target=framing_processor.frame_audio, args=(aud_rcv,
                                                    frm_snd,
                                                    RATE))
    frm_p.start()
    print ('started frm')

    last_heartbeat = time.time() + 20  # to allow for startup time
    while True:
        if not frm_p.is_alive():
            logger.warning("FRAME DIED...Restarting")
        if not aud_p.is_alive():
            logger.warning("AUDIO PROCESS DIED...Restarting")
            aud_p = multiprocessing.Process(
                target=audio_processor.record_audio, args=(aud_snd,
                                                           rec_snd,  # None
                                                           RATE,
                                                           CHUNK,
                                                           IDX,
                                                           CHANNELS))
            aud_p.start()
        elif not rec_p.is_alive():
            logger.warning("RECORDING PROCESS DIED...Restarting")
            rec_p = multiprocessing.Process(
                target=audio_archive_processor.archive_audio, args=(rec_rcv,
                                                                    RATE,
                                                                    CHANNELS,
                                                                    AUD_ARCHIVE_SECONDS,
                                                                    '/archive'
                                                                    ))
            rec_p.start()
        else:
            time.sleep(.2)


if __name__ == "__main__":
    logger.error('staring inference')
    inf_thread = Thread(target=infer, args=(frm_rcv,))
    inf_thread.start()
    logger.error('started inference')
    aud_ctrl_thread = Thread(
        target=audio_control_processor, args=(aud_cmd_snd,))
    aud_ctrl_thread.start()
    dmp_thread = Thread(target=dump_processor, args=(cmd_snd,))
    dmp_thread.start()
    mon_thread = Thread(target=monitor_processes, args=())
    mon_thread.start()

    mon_thread.join()
    inf_thread.join()
    dmp_thread.join()
