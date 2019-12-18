""" PI core inference audio archive processor """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 2019"
__credits__ = []
__license__ = "GPL"

import os
import numpy as np
import time
from collections import deque
import datetime
from . import logger


def archive_audio(rec_rcv,
                  rate,
                  channels=2,
                  duration=5,  # seconds
                  archive_root='/tmp'
                  ):

    def _get_audio_archive_f(dir, rate, duration, channels):
        fname = f'{int(time.time())}-{duration}-{rate}-{channels}.raw'
        #now = datetime.datetime.utcnow()
        #now_tt = now.timetuple()
        #arc_dir = os.path.join(dir, str(now_tt.tm_year), str(now_tt.tm_yday))
        #if not os.path.exists(arc_dir):
        #    os.makedirs(name=arc_dir)

        return open(os.path.join(dir, fname), 'wb')

    frames_written = 0
    frames_per_file = duration * rate
    open_archive = _get_audio_archive_f(
        dir=archive_root, rate=rate, duration=duration, channels=channels)

    while True:
        if rec_rcv.poll():
            data = rec_rcv.recv()  # numpy ndarray (frames,channels)

            if frames_written + data.shape[0] > frames_per_file:
                data[:frames_per_file -
                     frames_written, ...].tofile(open_archive)
                open_archive.close()
                open_archive = _get_audio_archive_f(
                    dir=archive_root, rate=rate, duration=duration, channels=channels)
                data[frames_per_file -
                     frames_written:, ...].tofile(open_archive)
                frames_written = frames_per_file - frames_written
            else:
                data.tofile(open_archive)
                frames_written += data.shape[0]
        else:
            time.sleep(.05)
