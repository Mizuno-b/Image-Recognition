python3 - << 'EOF'
import cv2
import numpy as np
import threading
import time
import os
from flask import Flask, Response
from ultralytics import YOLO

# =========================
# Flask
# =========================
app = Flask(__name__)

output_frame = None
lock = threading.Lock()

# =========================
# キャリブ
# =========================
CALIB_FILE = "stereo_camera_calibration.npz"

if not os.path.exists(CALIB_FILE):
    print("❌ calibration file not found")
    exit()

calib = np.load(CALIB_FILE)

map1_l = calib["map1_l"]
map2_l = calib["map2_l"]
map1_r = calib["map1_r"]
map2_r = calib["map2_r"]

# =========================
# カメラ
# =========================
capL = cv2.VideoCapture(0)
capR = cv2.VideoCapture(2)

for cap in [capL, capR]:
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# =========================
# YOLO
# =========================
model = YOLO("yolov8n.pt")

# =========================
# StereoBM
# =========================
stereo = cv2.StereoBM_create(
    numDisparities=96,
    blockSize=15
)

stereo.setTextureThreshold(10)
stereo.setUniquenessRatio(10)

# =========================
# パラメータ
# =========================
BASELINE = 0.071
FOCAL = 630

# ★スケール（実測補正）
SCALE = 1.20

# ★距離ゾーン（スケール適用済み）
NEAR_MIN = 0.35 * SCALE
NEAR_MAX = 2.3 * SCALE

# =========================
# フレーム共有
# =========================
frameL = None
frameR = None

# =========================
# カメラスレッド
# =========================
def cam_loop():
    global frameL, frameR

    while True:
        retL, l = capL.read()
        retR, r = capR.read()

        if not retL or not retR:
            continue

        frameL = l
        frameR = r

# =========================
# 処理スレッド
# =========================
def process_loop():
    global output_frame

    while True:

        if frameL is None or frameR is None:
            time.sleep(0.01)
            continue

        left = frameL.copy()
        right = frameR.copy()

        # 左右補正
        left, right = right, left

        # キャリブ補正
        left = cv2.remap(left, map1_l, map2_l, cv2.INTER_LINEAR)
        right = cv2.remap(right, map1_r, map2_r, cv2.INTER_LINEAR)

        grayL = cv2.cvtColor(left, cv2.COLOR_BGR2GRAY)
        grayR = cv2.cvtColor(right, cv2.COLOR_BGR2GRAY)

        disp = stereo.compute(grayL, grayR).astype(np.float32) / 16.0

        valid = (disp > 8) & (disp < 128)

        depth = np.ones_like(disp) * 10
        depth[valid] = (FOCAL * BASELINE) / disp[valid]

        # =========================
        # YOLO
        # =========================
        results = model.predict(left, classes=[0], verbose=False)

        draw = left.copy()
        overlay = draw.copy()

        for r in results:
            for box in r.boxes:

                x1, y1, x2, y2 = map(int, box.xyxy[0])

                # ROI（中央）
                cx1 = int(x1 + (x2 - x1) * 0.40)
                cx2 = int(x1 + (x2 - x1) * 0.60)
                cy1 = int(y1 + (y2 - y1) * 0.20)
                cy2 = int(y1 + (y2 - y1) * 0.80)

                mask = np.zeros_like(valid, dtype=bool)
                mask[cy1:cy2, cx1:cx2] = True

                vals = depth[mask & valid]

                text = "---"
                color = (0, 255, 0)

                if len(vals) > 20:

                    vals = vals[np.isfinite(vals)]

                    # ★中央値＋スケール
                    d = np.median(vals) * SCALE

                    text = f"{d:.2f}m"

                    # =========================
                    # 距離判定（スケール済み）
                    # =========================
                    if NEAR_MIN <= d <= NEAR_MAX:
                        color = (0, 0, 255)   # 赤（危険）
                    elif d < NEAR_MIN:
                        color = (255, 255, 0) # 黄（近すぎ）
                    else:
                        color = (0, 255, 0)   # 緑

                # 枠
                cv2.rectangle(draw, (x1, y1), (x2, y2), color, 2)

                # 距離表示
                w, h = 90, 30
                tx1 = x2 - w
                ty1 = y1
                tx2 = x2
                ty2 = y1 + h

                cv2.rectangle(draw, (tx1, ty1), (tx2, ty2), (0, 0, 0), -1)

                cv2.putText(
                    draw,
                    text,
                    (tx1 + 5, ty2 - 8),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2
                )

        out = cv2.addWeighted(draw, 0.5, overlay, 0.5, 0)

        with lock:
            output_frame = out.copy()

# =========================
# Flask
# =========================
def gen():
    global output_frame

    while True:
        with lock:
            if output_frame is None:
                continue

            _, buf = cv2.imencode(".jpg", output_frame)
            frame = buf.tobytes()

        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" +
               frame + b"\r\n")

@app.route("/")
def index():
    return Response(gen(),
        mimetype="multipart/x-mixed-replace; boundary=frame")

# =========================
# MAIN
# =========================
if __name__ == "__main__":

    t1 = threading.Thread(target=cam_loop, daemon=True)
    t2 = threading.Thread(target=process_loop, daemon=True)

    t1.start()
    t2.start()

    print("🚀 RUNNING SYSTEM (SCALE ENABLED)")
    print("➡ http://192.168.1.10:5000")

    app.run(host="0.0.0.0", port=5000, threaded=True)
EOF