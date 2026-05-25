python3 -c "
import cv2
import numpy as np
import os
from ultralytics import YOLO

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

BASELINE = 0.071 
FOCAL_LENGTH = 630 
ALERT_LIMIT = 0.70 

stereo = cv2.StereoBM_create(numDisparities=128, blockSize=15) 
stereo.setMinDisparity(0)                                      
stereo.setTextureThreshold(10)                                 
stereo.setUniquenessRatio(10)                                  
stereo.setSpeckleWindowSize(150)
stereo.setSpeckleRange(4)

WINDOW_NAME = 'Safety Monitor (Fix Distance Display)'
cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
cv2.resizeWindow(WINDOW_NAME, 800, 600)

print('==> 【描画修正版】システム起動！ [ESCキーで終了]')

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
            
            # 危険ゾーンの赤染め処理
            danger_pixel_mask = zone_mask & person_mask
            red_overlay[danger_pixel_mask] = [0, 0, 255]

            # 人の枠内の最小距離を計算
            valid_person_distances = distance_map[person_mask & valid_mask]
            
            dist_text = '--- m'
            box_color = (0, 255, 0) # 通常は緑

            if len(valid_person_distances) > 0:
                min_dist = np.min(valid_person_distances)
                dist_text = f'{min_dist:.2f}m'
                if min_dist <= ALERT_LIMIT:
                    box_color = (0, 0, 255) # 70cm以内で赤枠

            # 外枠を先に描画
            cv2.rectangle(draw_frame, (x1, y1), (x2, y2), box_color, 2)
            
            # 文字を描く位置を決める（画面外にはみ出さない対策）
            text_y = y1 - 10 if y1 - 10 > 20 else y1 + 20
            
            # 黒い「縁取り」をつけて文字を確実に目立たせる（背景塗りつぶしをやめ、直接文字を描画）
            cv2.putText(draw_frame, dist_text, (x1 + 5, text_y), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4, cv2.LINE_AA) # 黒い影
            cv2.putText(draw_frame, dist_text, (x1 + 5, text_y), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA) # 白い文字

    # 最後に半透明ブレンド
    cv2.addWeighted(red_overlay, 0.5, draw_frame, 0.5, 0, draw_frame)

    cv2.imshow(WINDOW_NAME, draw_frame)
    if cv2.waitKey(1) & 0xFF == 27: break

cap0.release(); cap2.release(); cv2.destroyAllWindows()
"
