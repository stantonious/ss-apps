from flask import Flask, request, send_file, make_response, render_template
import time
from subprocess import Popen, PIPE
import os
app = Flask(__name__)


@app.route("/test", methods=['POST', 'GET'])
def decode_raw():
    url_name = '/tmp/client-dump.raw'

    popen_args = ['ffmpeg', '-f', 's16le', '-ac', '2', '-ar',
                  '16000', '-i', url_name, '-f', 'mp3', 'pipe:1']

    proc = Popen(popen_args, stdout=PIPE)

    res = make_response(send_file(proc.stdout,
                                  mimetype='audio/mpeg',
                                  attachment_filename='test-{}.mp3'.format(time.time())))
    res.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    res.headers["Pragma"] = "no-cache"
    res.headers["Expires"] = "0"
    res.headers['Cache-Control'] = 'public, max-age=0'

    return res


if __name__ == '__main__':
    app.run()
