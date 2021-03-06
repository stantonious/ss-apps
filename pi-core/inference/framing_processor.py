""" PI core inference framing processor """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 2019"
__credits__ = []
__license__ = "GPL"

import numpy as np
import time

from . import logger

shift_window = 1
num_secs_to_process = 1


def frame_audio(aud_rcv,
                frm_snd,
                rate,
                ):
    batches = None
    while True:
        data = aud_rcv.recv()
        batches = np.concatenate(
            (batches, data), axis=0) if batches is not None else data
        # batches.extend(data)

        if len(batches) >= rate * num_secs_to_process:  # CHUNK * num_batches:
            normalized_audio, batches = np.split(
                batches, [rate * num_secs_to_process])
            # Convert to [-1.0, +1.0]
            normalized_audio = (normalized_audio / 32768.0).astype(np.float32)
            frm_snd.send((time.time(), normalized_audio))
