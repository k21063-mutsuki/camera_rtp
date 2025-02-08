import av
import cv2
import numpy as np
import client
import time
import shared
import threading

lock = threading.Lock()

# SDPファイルを取得
response = client.connection()
results = response.json()
sdp_content = results.get("sdp", "")
with open("received_stream.sdp", "w") as f:
    f.write(sdp_content)
print("SDPファイルを received_stream.sdp として保存しました。")

# 解像度を取得
resolution = results.get("resolution", {})
width = resolution.get("width")
height = resolution.get("height")

sdp = "received_stream.sdp"

# RTPストリームの取得
container = av.open(sdp, options={
    'protocol_whitelist': 'file,udp,rtp',
    'fflags': 'nobuffer',
    'flags': 'low_delay',
    'analyzeduration': '1000000',
    'probesize': '500000'
})

frame_rate = 30  
frame_time = 1.0 / frame_rate  

for frame in container.decode(video=0):
    start_time = time.time()

    img = frame.to_ndarray(format='bgr24')

    with lock:
        shared.global_value = img  # 共有メモリに保存

    cv2.imshow('RTP Stream', img)

    elapsed_time = time.time() - start_time
    sleep_time = max(0, frame_time - elapsed_time)
    time.sleep(sleep_time)  

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

container.close()
cv2.destroyAllWindows()
