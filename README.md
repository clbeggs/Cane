

### Table of Contents
---

- [Important ROS Topics](#important-ros-topics)
- [Building](#building)
- [Running](#running)
- [Config File](#config-file)
- [Building the Documentation](#building-the-documentation)
- [SLAM Library](#slam-library)
- [Semantic Segmentation Library](#semantic-segmentation-library)
- [Todo](#todo)

---

## Project Layout
```
.
├── lib                          # External libraries
├── video_stream                 # Streams video from bagfile or Realsense Cam.
├── segmentation                 # Takes streamed video and outputs prediction masks + classes
├── obj_inference                # Extracts distance and center point from pred. masks
└── slam                         # Uses center points of objects to map + localize
```


## Important ROS Topics

- [`/seg/prediction`](./segmentation/msg/Prediction.msg) -- Segmentation masks, object centers, labels
- [`/video_stream/rgb_img`](http://docs.ros.org/en/melodic/api/sensor_msgs/html/msg/Image.html) -- RGB input image
- [`/video_stream/depth_img`](http://docs.ros.org/en/melodic/api/sensor_msgs/html/msg/Image.html) -- Depth image input
- [`/inference/obj_inference`](./obj_inference/msg/Objects.msg) -- Distances, relative positions of objects, labels


## Output

 - label
 - distance
 - Relative location from cane
 - class probability
 - obj. width




## Dependencies

- pygame
- ROS Melodic, built with Python3


## Building

```bash
### SOURCE ROS FIRST ###

# make cane workspace 
$ mkdir -p cane_ws/src && cd cane_ws/src
$ git clone https://github.com/clbeggs/Cane.git

# cd to cane_ws
$ cd .. && catkin_make

# Source cane_ws
$ source devel/setup.bash  
```

## Running

First, [edit the config file](#config-file)

```bash
# Start segmentation model node
$ roslaunch segmentation segmentation.launch

# Start object inference node
$ roslaunch obj_inference inference.launch

# Start video stream
$ roslaunch video_stream streamer.launch
```


## Config File

Entries to edit:
- RGB + Depth map input source -- [video_stream](./video_stream/README.md)  
    - `ROSBag` - Input video from bag file
    - `RawFiles` - input video from rgb directory + depth directory
        - requires `rgb_dir` and `depth_dir` specifications in config file.
    - `RealSense` - input video from connected RealSense Came
- Semantic Segmentation Model -- [segmentation](./segmentation/README.md)
    - `detectron` - Facebook's [Detectron2 model](https://github.com/facebookresearch/detectron2)

#### Example:
```yaml
### Video Input Config
video_stream: "ROSBag"                            

bag_file: "./segmentation/bags/rgbd.bag"          # Input ROSbag file

topics:                                           # Check available topics via rosbag info <bag_file>
    - "/camera/depth/image_rect_raw/compressed"
    - "/camera/color/image_raw/compressed"

visualize: True                                   # Visualize input images via cv2.namedWindow

### Segmentation model config
segmentation_model: "detectron"                  
```


## Building the Documentation

## TODO: 

- Make video streamer asynch, use multiprocessing like torch DataLoader
- example script
- Sphinx documentation
