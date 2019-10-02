""" PI core inference embedding processor """
__author__ = "Bryan Staley"
__copyright__ = "Copyright 2019"
__credits__ = []
__license__ = "GPL"

from vggish import vggish_input
from vggish import vggish_postprocess
import tensorflow as tf
import numpy as np
import time


def generate_embeddings(frm_rcv,
                        emb_snd,
                        mon_snd,
                        emb_rec_snd=None,
                        aud_cmd_rcv=None,
                        RATE=16000):
    pproc = vggish_postprocess.Postprocessor(
        '/opt/vggish/vggish_pca_params.npz')

    # Load TFLite model and allocate tensors.
    interpreter = tf.lite.Interpreter(
        model_path="/opt/soundscape/vggish.tflite")
    interpreter.allocate_tensors()

    # Get input and output tensors.
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    print ('starting embedding processor', input_details[0])

    resume_at = True
    while True:
        try:
            mon_snd.send(time.time())

            if aud_cmd_rcv != None and aud_cmd_rcv.poll(.01):
                resume_at = aud_cmd_rcv.recv()
                print ('received embedding command:', resume_at)

            if frm_rcv.poll(.01) != None:
                aud_time, normalized_audio = frm_rcv.recv()
                if time.time() >= resume_at:
                    mel_samples = vggish_input.waveform_to_examples(
                        normalized_audio, RATE)
                    mel_samples = mel_samples.astype(dtype=np.float32)

                    interpreter.set_tensor(
                        input_details[0]['index'], mel_samples)
                    interpreter.invoke()
                    output_data = interpreter.get_tensor(
                        output_details[0]['index'])

                    postprocessed_batch = pproc.postprocess(output_data)
                    t = aud_time
                    for i,_n in enumerate(postprocessed_batch):
                        emb_snd.send((t, _n))
                        if emb_rec_snd:
                            emb_rec_snd.send(_n)
                        t += 1.0  # each sample is ~ 1 sec
            else:
                time.sleep(.3)
        except Exception as e:
            print ('Embeddings handler exception:', e)
            raise e
