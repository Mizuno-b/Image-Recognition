xhost +local:docker

sudo docker run --runtime nvidia -it --rm \
    --network host \
    --ipc=host \
    --privileged \
    --device /dev/video0 \
    --device /dev/video1 \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -v $HOME/.Xauthority:/root/.Xauthority \
    -e DISPLAY=$DISPLAY \
    -e XAUTHORITY=/root/.Xauthority \
    -e PYTORCH_NVML_DISABLE=1 \
    my_yolo_env:v2_engine
