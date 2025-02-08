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

        # protocol = request.args.get("protocol")
        # if protocol == "rtp" :
        #     fps = int(request.args.get("fps", 30))
        #     port = int(request.args.get("port", 9080))
        stream_thread = threading.Thread(target=self.start_rtp_stream, args=(parameters, ))
        stream_thread.daemon = True
        stream_thread.start()

        # return Response("rtp stream success")
        sdp_file = 'stream.sdp'
        while not os.path.exists(sdp_file):
            time.sleep(0.1)
        
        # SDPファイルの内容を読み込む
        with open(sdp_file, 'r') as f:
            sdp_content = f.read()

        width = data.get("width", 1280)  # デフォルト値を設定（例: 1280）
        height = data.get("height", 720)  # デフォルト値を設定（例: 720）

        response_data = {
            "sdp": sdp_content,
            "resolution": {
                "width": width,
                "height": height
            }
        }

        # SDPファイルの内容をHTTPレスポンスとして返す
        # return send_file(sdp_file, mimetype='application/sdp')
        return jsonify(response_data)

    def start_rtp_stream(self, parameters):
        # height, width, _ = shared.global_value.shape
        width = parameters.get("width", 1280)  # デフォルト値を設定（例: 1280）
        height = parameters.get("height", 720)  # デフォルト値を設定（例: 720）
        fps = parameters.get("fps")
        port = parameters.get("port")
        frame_rate = 30  # 目標のフレームレート
        frame_time = 1.0 / frame_rate  # 1フレームあたりの時間（秒）
        # command = [
        #     'ffmpeg',
        #     '-re', 
        #     '-f', 'rawvideo',
        #     '-pixel_format', 'bgr24',
        #     '-video_size', f'{str(width)}x{str(height)}',
        #     '-framerate', '30',
        #     '-i', '-',  
        #     '-vf', 'format=yuv420p',  # yuv420pに変換
        #     '-c:v', 'libx264', # '-c:v', 'h264_videotoolbox',
        #     '-preset', 'ultrafast', 
        #     '-tune', 'zerolatency',   # 低遅延設定を追加
        #     '-b:v', '800k',
        #     '-maxrate', '800k',
        #     '-bufsize', '2.4M',
        #     '-profile:v', 'baseline',  # ベースラインプロファイルを使用
        #     '-g', '30 * 2',  # キーフレームの更新頻度を2秒ごとに設定
        #     #'-level', '3.0',           # レベルを3.0に設定
        #     '-f', 'rtp',
        #     '-payload_type', '96',
        #     '-pkt_size', '1200',  # RTPパケットサイズ
        #     '-sdp_file', 'stream.sdp',
        #     f'rtp://127.0.0.1:{port}'
        # ]
        
        # command = [
        #     'ffmpeg',
        #     '-re',
        #     '-probesize', '5000000',  # プローブサイズを増やす
        #     '-analyzeduration', '10000000',  # 解析時間を増やす
        #     '-i', '-',  # 標準入力からH.264圧縮データを受け取る
        #     '-c:v', 'libx264',
        #     '-tune', 'zerolatency',   # 低遅延設定
        #     '-b:v', '800k',
        #     '-maxrate', '800k',
        #     '-bufsize', '2.4M',
        #     '-f', 'rtp',
        #     '-payload_type', '96',
        #     '-pkt_size', '1200',  # RTPパケットサイズ
        #     '-sdp_file', 'stream.sdp',
        #     f'rtp://127.0.0.1:{port}'
        # ]
        
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
            '-g', '30 * 2',  # キーフレームの更新頻度を2秒ごとに設定
            '-f', 'rtp',
            '-payload_type', '96',
            '-pkt_size', '1200',  # RTPパケットサイズ
            '-sdp_file', 'stream.sdp',
            f'rtp://127.0.0.1:{port}'
        ]

        # command = [
        #     'ffmpeg',
        #     '-re',
        #     '-probesize', '10M',  # プローブサイズを増加
        #     '-analyzeduration', '10000000',  # 解析時間を増加
        #     '-fflags', '+genpts',  # タイムスタンプを自動生成
        #     '-f', 'h264',
        #     '-r', '30',  # フレームレートを30 fpsに設定
        #     '-i', 'pipe:0',  # 標準入力からH.264エンコード済みデータを受け取る
        #     '-c:v', 'copy',  # エンコードせずにそのままコピー
        #     '-tune', 'zerolatency',  # 低遅延設定
        #     '-g', '60',  # キーフレーム更新間隔を60フレームごとに設定（2秒間隔）
        #     '-f', 'rtp',
        #     '-payload_type', '96',
        #     '-pkt_size', '1200',  # RTPパケットサイズ
        #     '-sdp_file', 'stream.sdp',
        #     f'rtp://127.0.0.1:{port}'
        # ]

        print("sdp file created")
    # # ffmpegプロセスを開始
        process = subprocess.Popen(command, stdin=subprocess.PIPE)

    #     while True:
    #         with shared.lock:
    #             if shared.global_value is not None:
    #                 if self.handlers:
    #                     func = self.handlers[0]  # self.handlers が1つの関数である前提
    #                     results = func()
    #                     # results = [func() for func in self.handlers]
    #                     process.stdin.write(results.tobytes())

        fps = int(fps)
        print("fps:" + str(fps))
        frame_interval = 1.0 / fps
        results_frame = None

        while True:
            frame = shared.global_value
            start_time = time.time()

            if frame is not None:
                # handlersに格納された関数を実行
                if self.handlers:
                    results_frame = frame
                    for handler in self.handlers:
                    # 関数の引数リストを取得
                        sig = inspect.signature(handler)
                        func_params = sig.parameters.keys()
                    # parametersに関数の引数が揃っているか確認（frame以外の引数がparametersに含まれているか）
                        if all(param in parameters for param in func_params if param != 'data'):
            # 必要な引数をparametersから取得し、必要に応じてframeも追加して関数を実行
                            args = {param: parameters[param] for param in func_params if param in parameters}
            # 関数の引数に 'frame' がある場合は追加
                            if 'data' in func_params:
                                args['data'] = frame
                            # handlerを実行
                            results = handler(**args)

                            if results is not None:
                                results_frame = results
                else:
                    # handlersが空の場合はframeをそのままresults_frameに設定
                    results_frame = frame
                # if isinstance(results_frame, bytes):
                if isinstance(results_frame, bytes):
                    # print("frame_byte")
                    process.stdin.write(results_frame)
    
    # 送信速度を任意fpsに調整
            elapsed_time = time.time() - start_time
            sleep_time = max(0, frame_interval - elapsed_time)
            time.sleep(sleep_time)

    # while True:
    #     with lock:
    #         if global_frame is not None:
    #             # 最新フレームの輝度を調整
    #             adjusted_frame = adjust_brightness(global_frame, brightness)
    #             # フレームをパイプ経由でffmpegに渡す
    #             process.stdin.write(adjusted_frame.tobytes())

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
# # メインスレッドでサーバーを起動
# if __name__ == '__main__':
#     threading.Thread(target=run_server).start()
#     # run_server()