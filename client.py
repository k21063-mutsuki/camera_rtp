from flask import render_template, Flask, Response, request, jsonify
import cv2
import socket
from time import sleep
import ipget
import threading
import sys
import json
import requests
import connection
import time
import websockets
import asyncio
from string import Template
import subprocess
import numpy as np

app = Flask(__name__)

def connection():
    #ここはクラウドとの通信に変更予定
    json_open = open('param1.json', 'r')
    json_load = json.load(json_open)
    print(json_load)
    print("\n")

    service_type = json_load['service']['type']
    service_endpoint = json_load['service']['endpoint']

    if(service_type == "pull"):
        parameters = json_load.get('parameters', {})
        print(parameters)
        print("\n")

    response = requests.post(service_endpoint, data=json.dumps(parameters), headers={"Content-Type": "application/json"}, stream=True)
    print("send requests")
    # print (response)
    return response

def read_frames_from_ffmpeg(command, frame_queue, frame_size):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=10**8)
    while True:
        raw_frame = process.stdout.read(frame_size)
        if not raw_frame:
            break
        frame_queue.append(raw_frame)
        # print("格納されました")
    process.stdout.close()
    process.wait()

def frame_generator(sdp_file, width=1280, height=720):
    
    command = [
        'ffmpeg',
        '-protocol_whitelist', 'file,udp,rtp',
        '-fflags', 'nobuffer',
        '-flags', 'low_delay',
        '-fflags', 'discardcorrupt',  # 不正なフレームを破棄
        '-max_delay', '500000',       # 最大遅延を小さく設定（単位：マイクロ秒）
        '-probesize', '10M',        # プローブサイズを10MBに設定
        '-analyzeduration', '10000000', # 解析時間を増やして正確なストリーム情報を取得
        '-rtbufsize', '100M',         # リアルタイムバッファサイズの増加
        '-i', sdp_file,
        # '-c:v', 'copy',               # デコードせずコピー
        '-f', 'h264',                 # 出力フォーマットをH.264に設定
        'pipe:1'
    ]
    
    frame_size = width * height * 3  
    frame_queue = []

    frame_reader_thread = threading.Thread(target=read_frames_from_ffmpeg, args=(command, frame_queue, frame_size))
    frame_reader_thread.daemon = True
    frame_reader_thread.start()

    while True:
        if frame_queue:
            raw_frame = frame_queue.pop(0)
            frame = np.frombuffer(raw_frame, np.uint8).reshape((height, width, 3))
            yield frame