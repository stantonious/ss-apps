
import os
import glob
import sys

import tensorflow as tf
import pandas as pd
import numpy as np
from tensorflow.keras import datasets, layers, models
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import normalize
#from sklearn.decomposition import PCA
#pca = PCA(n_components=32)


SKIP_DIRS=['99','bak']

# load the data
d=[]
y=[]
i=0

for _dir,_,_ in os.walk(sys.argv[1]):
    if _dir == sys.argv[1] or os.path.basename(_dir) in SKIP_DIRS:
        continue # skip cwd
    _d=[]
    for _n in glob.glob(os.path.join(sys.argv[1],_dir,'*-emb.npy')):
        _d.append(np.asarray(np.load(_n)))
    _d=np.asarray(_d)
    d.append(_d)
    print ('appending ',len(_d),_dir)
    y.extend([i]*len(_d))
    i+=1

X=np.concatenate(d,axis=0)
Y=np.asarray(y)

np.save("Y.npy",Y)
#pca.fit(X)
#X = pca.transform(X)
#print ('pca exp',pca.explained_variance_ratio_,flush=True)

print ('shapes',X.shape,Y.shape,flush=True)

X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.15)

num_classes = len(d)
model = tf.keras.Sequential([#tf.keras.layers.Input((1024,)),
                             tf.keras.layers.Dense(16,input_shape=(1024,), activation="relu")  ,
                             #tf.keras.layers.BatchNormalization(),
                             tf.keras.layers.Dropout(.5),
                             #tf.keras.layers.Dense(8, activation="relu")  ,
                             #tf.keras.layers.Dropout(.2),
                             tf.keras.layers.Dense(num_classes,activation="softmax")
                            ])

print(model.summary())

model.compile(optimizer='adam',
              loss="sparse_categorical_crossentropy",
              metrics=['accuracy'])

history = model.fit(X_train, Y_train, epochs=100,
                    validation_data=(X_test, Y_test))

print (X_test.shape)
Y_pred = np.argmax(model.predict(X_test),-1)
print (Y_pred.shape)
print (Y_test.shape)
print(classification_report(Y_test, Y_pred))

model.save("ss-speech-classifier.h5", "wb")
