python3 -c "
import cv2
import numpy as np
import os
import threading
from flask import Flask, Response
from ultralytics import YOLO

# =========================
# Flask
# =========================
app = Flask(__name__)

output_frame = None
lock = threading.Lock()

# =========================
# キャリブファイル
# =========================
CALIB_FILE = 'stereo_camera_calibration.npz'

if not os.path.exists(CALIB_FILE):
    print('❌ 補正ファイルが見つかりません！')
    exit()

# =========================
# キャリブ読み込み
# =========================
calib_data = np.load(CALIB_FILE)

map1_l = calib_data['map1_l']
map2_l = calib_data['map2_l']

map1_r = calib_data['map1_r']
map2_r = calib_data['map2_r']

# =========================
# カメラ
# =========================
cap0 = cv2.VideoCapture(0)
cap2 = cv2.VideoCapture(2)

for cap in [cap0, cap2]:
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# =========================
# YOLO
# =========================
model = YOLO(
    'yolov8n.engine',
    task='detect'
)

# =========================
# パラメータ
# =========================
BASELINE = 0.071
FOCAL_LENGTH = 630
ALERT_LIMIT = 0.70

# =========================
# StereoBM
# =========================
stereo = cv2.StereoBM_create(
    numDisparities=128,
    blockSize=15
)

stereo.setMinDisparity(0)
stereo.setTextureThreshold(10)
stereo.setUniquenessRatio(10)
stereo.setSpeckleWindowSize(150)
stereo.setSpeckleRange(4)

# =========================
# メイン処理
# =========================
def processing_loop():

    global output_frame
    global lock

    while True:

        # =========================
        # カメラ取得
        # =========================
        ret0, frame0 = cap0.read()
        ret2, frame2 = cap2.read()

        if not (ret0 and ret2):
            continue

        # ====================================
        # 左右入れ替え
        # CAM0=右 / CAM2=左 対策
        # ====================================
        frame0, frame2 = frame2, frame0

        # =========================
        # ステレオ補正
        # =========================
        rect_left = cv2.remap(
            frame0,
            map1_l,
            map2_l,
            cv2.INTER_LINEAR
        )

        rect_right = cv2.remap(
            frame2,
            map1_r,
            map2_r,
            cv2.INTER_LINEAR
        )

        # =========================
        # グレースケール
        # =========================
        gray_left = cv2.cvtColor(
            rect_left,
            cv2.COLOR_BGR2GRAY
        )

        gray_right = cv2.cvtColor(
            rect_right,
            cv2.COLOR_BGR2GRAY
        )

        # =========================
        # disparity
        # =========================
        disparity = stereo.compute(
            gray_left,
            gray_right
        ).astype(np.float32) / 16.0

        # =========================
        # 有効視差のみ使用
        # =========================
        valid_mask = (
            (disparity > 2) &
            (disparity < 128)
        )

        # =========================
        # 距離マップ
        # =========================
        distance_map = np.ones_like(disparity) * 10.0

        distance_map[valid_mask] = (
            FOCAL_LENGTH * BASELINE
        ) / disparity[valid_mask]

        # =========================
        # 危険ゾーン
        # =========================
        zone_mask = (
            (distance_map > 0.01) &
            (distance_map <= ALERT_LIMIT)
        )

        # =========================
        # YOLO
        # =========================
        results = model.predict(
            rect_left,
            classes=[0],
            device=0,
            verbose=False
        )

        draw_frame = rect_left.copy()
        red_overlay = draw_frame.copy()

        # =========================
        # 人検知
        # =========================
        for r in results:

            for box in r.boxes:

                x1, y1, x2, y2 = map(
                    int,
                    box.xyxy[0]
                )

                # =========================
                # 中央のみ使用
                # =========================
                cx1 = int(
                    x1 + (x2 - x1) * 0.35
                )

                cx2 = int(
                    x1 + (x2 - x1) * 0.65
                )

                cy1 = int(
                    y1 + (y2 - y1) * 0.20
                )

                cy2 = int(
                    y1 + (y2 - y1) * 0.80
                )

                person_mask = np.zeros_like(
                    zone_mask,
                    dtype=bool
                )

                person_mask[
                    cy1:cy2,
                    cx1:cx2
                ] = True

                # =========================
                # 危険領域赤塗り
                # =========================
                danger_pixel_mask = (
                    zone_mask &
                    person_mask
                )

                red_overlay[
                    danger_pixel_mask
                ] = [0, 0, 255]

                # =========================
                # 距離取得
                # =========================
                valid_person_distances = distance_map[
                    person_mask & valid_mask
                ]

                dist_text = '--- m'
                box_color = (0, 255, 0)

                # =========================
                # 距離計算
                # =========================
                if len(valid_person_distances) > 30:

                    measured_dist = np.percentile(
                        valid_person_distances,
                        30
                    )

                    dist_text = (
                        f'{measured_dist:.2f}m'
                    )

                    if measured_dist <= ALERT_LIMIT:
                        box_color = (0, 0, 255)

                # =========================
                # 人物枠
                # =========================
                cv2.rectangle(
                    draw_frame,
                    (x1, y1),
                    (x2, y2),
                    box_color,
                    2
                )

                # =========================
                # 測定エリア表示
                # =========================
                cv2.rectangle(
                    draw_frame,
                    (cx1, cy1),
                    (cx2, cy2),
                    (255, 255, 0),
                    1
                )

                # =========================
                # テキスト位置
                # =========================
                text_y = (
                    y1 - 10
                    if y1 > 30
                    else y1 + 25
                )

                # 黒縁
                cv2.putText(
                    draw_frame,
                    dist_text,
                    (x1 + 5, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 0),
                    4,
                    cv2.LINE_AA
                )

                # 白文字
                cv2.putText(
                    draw_frame,
                    dist_text,
                    (x1 + 5, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA
                )

        # =========================
        # 半透明合成
        # =========================
        cv2.addWeighted(
            red_overlay,
            0.5,
            draw_frame,
            0.5,
            0,
            draw_frame
        )

        # =========================
        # 出力フレーム更新
        # =========================
        with lock:
            output_frame = draw_frame.copy()

# =========================
# Flask配信
# =========================
@app.route('/')

def index():

    def stream():

        while True:

            with lock:

                if output_frame is None:
                    continue

                ret, buffer = cv2.imencode(
                    '.jpg',
                    output_frame
                )

                if not ret:
                    continue

                frame_bytes = buffer.tobytes()

            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n'
                + frame_bytes +
                b'\r\n'
            )

    return Response(
        stream(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

# =========================
# 起動
# =========================
if __name__ == '__main__':

    t = threading.Thread(
        target=processing_loop,
        daemon=True
    )

    t.start()

    print('🚀 LAN配信サーバー起動')
    print('➡ ポート : 5000')

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        threaded=True
    )
"
