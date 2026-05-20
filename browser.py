python3 -c "
import cv2
import numpy as np
import os
import threading
from flask import Flask, Response
from ultralytics import YOLO

app = Flask(__name__)
output_frame = None
lock = threading.Lock()

CALIB_FILE = 'stereo_camera_calibration.npz'
if not os.path.exists(CALIB_FILE):
    print('❌ 補正ファイルが見つかりません！'); exit()

calib_data = np.load(CALIB_FILE)
map1_l, map2_l = calib_data['map1_l'], calib_data['map2_l']
map1_r, map2_r = calib_data['map1_r'], calib_data['map2_r']

cap0, cap2 = cv2.VideoCapture(0), cv2.VideoCapture(2)
for cap in [cap0, cap2]:
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

model = YOLO('yolov8n.engine', task='detect')

# パラメータ設定
BASELINE = 0.071 
FOCAL_LENGTH = 630 
ALERT_LIMIT = 0.70 

stereo = cv2.StereoBM_create(numDisparities=128, blockSize=15) 
stereo.setMinDisparity(0)                                      
stereo.setTextureThreshold(10)                                 
stereo.setUniquenessRatio(10)                                  
stereo.setSpeckleWindowSize(150)
stereo.setSpeckleRange(4)

def processing_loop():
    global output_frame, lock
    while True:
        ret0, frame0 = cap0.read()
        ret2, frame2 = cap2.read()
        if not (ret0 and ret2): continue

        rect_left = cv2.remap(frame0, map1_l, map2_l, cv2.INTER_LINEAR)
        rect_right = cv2.remap(frame2, map1_r, map2_r, cv2.INTER_LINEAR)

        gray_left = cv2.cvtColor(rect_left, cv2.COLOR_BGR2GRAY)
        gray_right = cv2.cvtColor(rect_right, cv2.COLOR_BGR2GRAY)
        
        disparity = stereo.compute(gray_left, gray_right).astype(np.float32) / 16.0

        distance_map = np.ones_like(disparity) * 10.0
        valid_mask = disparity > stereo.getMinDisparity()
        distance_map[valid_mask] = (FOCAL_LENGTH * BASELINE) / disparity[valid_mask]

        zone_mask = (distance_map > 0.01) & (distance_map <= ALERT_LIMIT)

        results = model.predict(rect_left, classes=[0], device=0, verbose=False)
        draw_frame = rect_left.copy()
        red_overlay = draw_frame.copy()

        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                person_mask = np.zeros_like(zone_mask)
                person_mask[y1:y2, x1:x2] = True
                
                danger_pixel_mask = zone_mask & person_mask
                red_overlay[danger_pixel_mask] = [0, 0, 255]

                valid_person_distances = distance_map[person_mask & valid_mask]
                dist_text = '--- m'
                box_color = (0, 255, 0)

                if len(valid_person_distances) > 0:
                    min_dist = np.min(valid_person_distances)
                    dist_text = f'{min_dist:.2f}m'
                    if min_dist <= ALERT_LIMIT:
                        box_color = (0, 0, 255)

                cv2.rectangle(draw_frame, (x1, y1), (x2, y2), box_color, 2)
                text_y = y1 - 10 if y1 - 10 > 20 else y1 + 20
                cv2.putText(draw_frame, dist_text, (x1 + 5, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4, cv2.LINE_AA)
                cv2.putText(draw_frame, dist_text, (x1 + 5, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)

        cv2.addWeighted(red_overlay, 0.5, draw_frame, 0.5, 0, draw_frame)

        with lock:
            output_frame = draw_frame.copy()

@app.route('/')
def index():
    def stream():
        while True:
            with lock:
                if output_frame is None: continue
                ret, buffer = cv2.imencode('.jpg', output_frame)
                if not ret: continue
                frame_bytes = buffer.tobytes()
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    return Response(stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    t = threading.Thread(target=processing_loop, daemon=True)
    t.start()
    print('🚀 【LAN配信サーバー起動】ポート: 5000')
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
"
