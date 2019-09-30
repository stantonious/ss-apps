'''
Created on Jan 4, 2019

@author: bstaley
'''
import os
import numpy as np
import time
from collections import deque
from . import logger


def record_audio(rec_rcv,
                 cmd_rcv,
                 emb_rcv,
                 rate,
                 channels=2,
                 buffer_len_secs=20,
                 buffer_dir='/tmp'
                 ):

    _buffer = deque(maxlen=buffer_len_secs * rate * channels)
    _emb_buffer = np.full((0,128),0)
    while True:
        if cmd_rcv.poll():
            dump_args = cmd_rcv.recv()
            print ('dump args',dump_args)
            dump_size = dump_args['size']
            logger.info('dumping:%s', dump_args)
            dump_fname = os.path.join(buffer_dir, 'dump.raw')
            emb_fname = os.path.join(buffer_dir, 'emb.npy')
            if dump_args['command'] == 'time':
                t=time.time()
                dump_fname = os.path.join(
                    buffer_dir, '{}-{}-{}-dump.raw'.format(t,rate,channels))
                emb_fname = os.path.join(
                    buffer_dir, '{}-emb.npy'.format(t))
            elif dump_args['command'] == 'default':
                pass
            else:
                dump_fname = os.path.join(
                    buffer_dir, '{}-{}-{}-dump.raw'.format(dump_args['command'],rate,channels))
                emb_fname = os.path.join(
                    buffer_dir, '{}-emb.npy'.format(dump_args['command']))

            print ('trying to write',dump_fname)
            np.asarray(_buffer,dtype=np.int16)[-dump_size*channels*rate:].tofile(dump_fname)
            np.save(emb_fname,_emb_buffer[-dump_size:])

        elif rec_rcv.poll():
            data = rec_rcv.recv()
            if data.ndim > 1:
                _buffer.extend(data.flatten().tolist())
            else:
                _buffer.extend(data.tolist())
        elif emb_rcv.poll():
            data = emb_rcv.recv()
            _emb_buffer = np.concatenate((_emb_buffer,data.reshape(1,-1)),axis=0)
            _emb_buffer = _emb_buffer[-buffer_len_secs:,...]
        else:
            time.sleep(.1)
