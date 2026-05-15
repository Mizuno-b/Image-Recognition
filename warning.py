python3 -c "
from ultralytics import YOLO
import cv2
import numpy as np
import time

cap0 = cv2.VideoCapture(0)
cap2 = cv2.VideoCapture(2)

for cap in [cap0, cap2]:
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

model = YOLO('yolov8n.engine', task='detect')

BASELINE = 0.114 
FOCAL_LENGTH = 630 

# --- 安全装置用の変数 ---
ALERT_DISTANCE = 0.5   
detect_counter = 0     
ALERT_THRESHOLD = 3    

while True:
    ret0, frame0 = cap0.read()
    ret2, frame2 = cap2.read()
    if not (ret0 and ret2): continue

    results = model.predict(frame0, classes=[0], device=0, verbose=False)
    
    # 描画用フレームは左カメラ(frame0)のみを使用
    draw_frame = frame0.copy()
    
    any_person_too_close = False 

    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cx_left = (x1 + x2) // 2
            cy_left = (y1 + y2) // 2

            tw, th = 20, 20
            tx1, ty1 = cx_left - tw//2, cy_left - th//2
            if tx1 < 0 or ty1 < 0 or tx1+tw > 640: continue
            template = frame0[ty1:ty1+th, tx1:tx1+tw]
            
            search_area = frame2[ty1:ty1+th, :]
            res = cv2.matchTemplate(search_area, template, cv2.TM_CCOEFF_NORMED)
            _, _, _, max_loc = cv2.minMaxLoc(res)
            cx_right = max_loc[0] + tw//2

            disparity = cx_left - cx_right
            
            if disparity > 2:
                distance = (FOCAL_LENGTH * BASELINE) / disparity
                
                if distance < ALERT_DISTANCE:
                    any_person_too_close = True
                    color = (0, 0, 255) 
                else:
                    color = (0, 255, 0) 
                
                cv2.rectangle(draw_frame, (x1, y1), (x2, y2), color, 3)
                label = f'{distance:.2f}m'
                text_y = y1 + 35 if y1 < 50 else y1 - 10
                cv2.putText(draw_frame, label, (x1, text_y), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)

    if any_person_too_close:
        detect_counter += 1
    else:
        detect_counter = max(0, detect_counter - 1)

    if detect_counter >= ALERT_THRESHOLD:
        # 画面全体に赤いオーバーレイ（半透明）
        overlay = draw_frame.copy()
        cv2.rectangle(overlay, (0, 0), (640, 480), (0, 0, 255), -1)
        cv2.addWeighted(overlay, 0.3, draw_frame, 0.7, 0, draw_frame)
        
        # 警告文字
        cv2.putText(draw_frame, '!!! WARNING !!!', (130, 240), 
                    cv2.FONT_HERSHEY_DUPLEX, 1.5, (255, 255, 255), 4)

    # 1画面(640x480)をそのまま表示するか、少し大きくして表示
    cv2.imshow('Safety Monitor', draw_frame)
    if cv2.waitKey(1) & 0xFF == 27: break

cap0.release(); cap2.release(); cv2.destroyAllWindows()
"
