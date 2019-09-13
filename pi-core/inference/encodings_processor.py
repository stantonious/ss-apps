'''
Created on Jan 4, 2019

@author: bstaley
'''
import numpy as np
import tensorflow as tf

running_avg_win = 100
running_avg_conv_win = 4
running_avg = None


def infer(frm_rcv,
          seq_len=10,
          shift_window=1,
          infrence_cb=None):
    
    def def_cb(y ,time_step):
        print y, time_step
        


    infrence_cb = infrence_cb or def_cb
    
    # Load TFLite model and allocate tensors.
    interpreter = tf.contrib.lite.Interpreter(model_path="/opt/soundscape/ss-autoencoder.tflite")
    interpreter.allocate_tensors()

    # Get input and output tensors.
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    print 'starting encodings processor', input_details[0]
    batch_embeddings = []
    batch_times = []

    while True:
    #    print 'emb q size', in_q.qsize()
        t, embedding = frm_rcv.recv(True)
        batch_embeddings.append(embedding)
        batch_times.append(t)
        # print 'got an inf record'
        
        if len(batch_embeddings) >= seq_len:
               
            # sequential_input = tf.keras.preprocessing.sequence.pad_sequences(batch_embeddings[:10], 10)
            sequential_input = np.expand_dims(np.asarray(batch_embeddings[:seq_len]), 0)
            sequential_input = sequential_input.astype(dtype=np.float32)
            interpreter.set_tensor(input_details[0]['index'], sequential_input)
            interpreter.invoke()
            print 'output',output_details
            output_data = interpreter.get_tensor(output_details[0]['index'])
            
            infrence_cb(output_data,
                        batch_times[seq_len - 1])

            batch_embeddings = batch_embeddings[shift_window:]
            batch_times = batch_times[shift_window:]
