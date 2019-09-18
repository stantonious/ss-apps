'''
Created on Jan 4, 2019

@author: bstaley
'''
import os
import numpy as np
import time
from collections import deque
import gzip
from . import logger


def archive_audio(rec_rcv,
                  rate,
                  channels=2,
                  duration=5,  # seconds
                  archive_dir='/tmp'
                  ):

    def _get_audio_archive_f(dir, rate, duration, channels):
        fname = f'{time.time()}-{duration}-{rate}-{channels}.raw'
        return gzip.open(os.path.join(dir, fname), 'wb')

    frames_written = 0
    frames_per_file = duration * rate
    open_archive = _get_audio_archive_f(
        dir=archive_dir, rate=rate, duration=duration, channels=channels)

    while True:
        if rec_rcv.poll():
            data = rec_rcv.recv()  # numpy ndarray (frames,channels)

            if frames_written + data.shape[0] > frames_per_file:
                data[:frames_per_file -
                     frames_written, ...].tofile(open_archive)
                open_archive.close()
                open_archive = _get_audio_archive_f(
                    dir=archive_dir, rate=rate, duration=duration, channels=channels)
                data[frames_per_file -
                     frames_written:, ...].tofile(open_archive)
                frames_written = frames_per_file - frames_written
            else:
                data.tofile(open_archive)
                frames_written += data.shape[0]
        else:
            time.sleep(.05)
