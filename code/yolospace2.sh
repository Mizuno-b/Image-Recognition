xhost +local:docker

sudo docker run --runtime nvidia -it --rm \
    --network host \
    --ipc=host \
    --privileged \
    --device /dev/video0 \
    --device /dev/video1 \
    --device /dev/video2 \
    -v /proc/device-tree/compatible:/proc/device-tree/compatible:ro \
    -v /dev:/dev \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -v $HOME/.Xauthority:/root/.Xauthority \
    -v /home/mizuno/stereo_camera_calibration.npz:/workspace/stereo_camera_calibration.npz \
    -e DISPLAY=$DISPLAY \
    -e XAUTHORITY=/root/.Xauthority \
    -e PYTORCH_NVML_DISABLE=1 \
    my_yolo_env:v4_gpio
