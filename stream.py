import cv2
import subprocess
import numpy as np
import shared  # sharedモジュールをインポート
import threading
from server import MultiThreadedServer

lock = threading.Lock()

def capture_camera():
    cap = cv2.VideoCapture(0) 
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    # カメラの解像度を取得
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
 
    # # FFmpegでH.264エンコードを行うコマンド
    # command = [
    #     'ffmpeg',
    #     '-re', 
    #     '-f', 'rawvideo',
    #     '-pixel_format', 'bgr24',
    #     '-video_size', f'{str(width)}x{str(height)}',
    #     '-framerate', '30',
    #     '-i', '-',  
    #     '-vf', 'format=yuv420p',
    #     '-c:v', 'libx264',
    #     '-preset', 'ultrafast',
    #     '-tune', 'zerolatency',
    #     '-b:v', '800k',
    #     '-f', 'h264',
    #     'pipe:1'
    # ]
    
    command = [
        'ffmpeg',
        '-re', 
        '-f', 'rawvideo',
        '-pixel_format', 'bgr24',
        '-video_size', f'{str(width)}x{str(height)}',
        '-framerate', '30',
        '-i', '-',  
        '-vf', 'format=yuv420p',  # yuv420pに変換
        '-c:v', 'libx264', # '-c:v', 'h264_videotoolbox',
        '-preset', 'ultrafast', 
        '-tune', 'zerolatency',   # 低遅延設定を追加
        '-b:v', '800k',
        '-maxrate', '800k',
        '-bufsize', '2.4M',
        '-profile:v', 'baseline',  # ベースラインプロファイルを使用
        '-g', '30 * 2',  # キーフレームの更新頻度を2秒ごとに設定
        '-f', 'h264',
        'pipe:1'
    ]
    
    command2 = [
        'ffmpeg',
        '-protocol_whitelist', 'file,udp,rtp,pipe',
        '-i', 'pipe:1',
        '-f', 'rawvideo',
        '-pix_fmt', 'bgr24',
        '-an',
        'pipe:1'
    ]
    
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0)

    frame_data = b''
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # FFmpegプロセスにフレームを送信
        process.stdin.write(frame.tobytes())
        
        # FFmpegからH.264でエンコードされたデータを読み取り
        data = process.stdout.read(8192)
        frame_data += data

        # 開始コードで1フレーム分のデータを特定
        while b'\x00\x00\x00\x01' in frame_data:
            start_idx = frame_data.find(b'\x00\x00\x00\x01')
            next_start_idx = frame_data.find(b'\x00\x00\x00\x01', start_idx + 4)
            
            # 次の開始コードが見つかった場合、1フレーム分のデータとして扱う
            if next_start_idx != -1:
                h264_frame = frame_data[start_idx:next_start_idx]
                frame_data = frame_data[next_start_idx:]
                
                # グローバル変数に格納
                with lock:
                    shared.global_value = h264_frame
                    # print("start: " + str(h264_frame) + " :finish")
            else:
                # まだフレームの終わりが見つかっていない場合は次のループへ
                break
        
        # フレームを表示
        cv2.imshow("Stream Data", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # リソースを解放
    cap.release()
    process.stdin.close()
    process.stdout.close()
    process.wait()
    
def adjust_brightness(data, brightness):
    adjusted = cv2.convertScaleAbs(data, alpha=brightness)
    return adjusted

def delay_fps():
    time.sleep(1/30)
    print("wait fps")
    
handlers = []

server = MultiThreadedServer(handlers=handlers)
# server_thread = threading.Thread(target=server.start)
# server_thread.start()
server.run_server()

capture_camera()