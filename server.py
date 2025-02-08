from flask import Flask, jsonify, request, Response, send_file
import threading
import subprocess
import shared
import cv2
import time 
import inspect
import os

class MultiThreadedServer:
    def __init__(self, handlers, host='0.0.0.0', port=8080):
        self.app = Flask(__name__)
        self.host = host
        self.port = port
        self.handlers = handlers if handlers else []

        # エンドポイントの設定
        self.app.add_url_rule('/video_feed', 'video_feed', self.video_feed, methods=['POST'])
        
    def video_feed(self):
        print("request success")
        data = request.get_json()
        print(data)
        if not data :
            print("test")
            return Response("Invalid JSON data", status=400)
        
        parameters = data

        stream_thread = threading.Thread(target=self.start_rtp_stream, args=(parameters, ))
        stream_thread.daemon = True
        stream_thread.start()

        sdp_file = 'stream.sdp'
        while not os.path.exists(sdp_file):
            time.sleep(0.1)
        
        # SDPファイル読み込み
        with open(sdp_file, 'r') as f:
            sdp_content = f.read()

        width = data.get("width", 1280)  
        height = data.get("height", 720)  

        response_data = {
            "sdp": sdp_content,
            "resolution": {
                "width": width,
                "height": height
            }
        }

        return jsonify(response_data)

    def start_rtp_stream(self, parameters):
        width = parameters.get("width", 1280)  
        height = parameters.get("height", 720)  
        fps = parameters.get("fps")
        port = parameters.get("port")
        frame_rate = 30  
        frame_time = 1.0 / frame_rate  
        
        command = [
            'ffmpeg',
            '-re',
            '-probesize', '10M',  # プローブサイズを増加
            '-analyzeduration', '10000000',  # 解析時間を増加
            '-fflags', '+genpts',  # タイムスタンプを自動生成
            '-f', 'h264', 
            # '-s', f'{width}x{height}',  # 解像度を明示的に指定
            '-i', 'pipe:0',  # 標準入力からH.264エンコード済みデータを受け取る
            '-c:v', 'copy',  # エンコードせずにそのままコピー
            '-tune', 'zerolatency',  # 低遅延設定
            '-b:v', '1M',
            '-maxrate', '1M',
            '-bufsize', '2.4M',
            '-g', '30 * 2',  
            '-f', 'rtp',
            '-payload_type', '96',
            '-pkt_size', '1200',  # RTPパケットサイズ
            '-sdp_file', 'stream.sdp',
            f'rtp://127.0.0.1:{port}'
        ]


        print("sdp file created")
    # # ffmpegプロセスを開始
        process = subprocess.Popen(command, stdin=subprocess.PIPE)

        fps = int(fps)
        print("fps:" + str(fps))
        frame_interval = 1.0 / fps
        results_frame = None

        while True:
            frame = shared.global_value
            start_time = time.time()

            if frame is not None:
                
                if self.handlers:
                    results_frame = frame
                    for handler in self.handlers:
                    
                        sig = inspect.signature(handler)
                        func_params = sig.parameters.keys()
                    
                        if all(param in parameters for param in func_params if param != 'data'):
           
                            args = {param: parameters[param] for param in func_params if param in parameters}
           
                            if 'data' in func_params:
                                args['data'] = frame
                            # handlerを実行
                            results = handler(**args)

                            if results is not None:
                                results_frame = results
                else:
                    
                    results_frame = frame
            
                if isinstance(results_frame, bytes):

                    process.stdin.write(results_frame)
    
    # fps調整
            elapsed_time = time.time() - start_time
            sleep_time = max(0, frame_interval - elapsed_time)
            time.sleep(sleep_time)

    def test(self):
        print("test success")
        if self.handlers:
            results = [func() for func in self.handlers]  # 各関数を実行

    def start(self):
        """HTTPサーバをマルチスレッドで起動する"""
        self.app.run(host=self.host, port=self.port, threaded=True)

    # サーバを起動するためのラッパー関数
    def run_server(self):
        start_thread = threading.Thread(target=self.start)
        start_thread.daemon = True
        start_thread.start()
