#!/usr/bin/env python
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Optional, Tuple, Union

import message_filters
import numpy as np
import rospy
#  import segmentation_models_pytorch as smp
import torch
import torch.nn as nn
from cv_bridge import CvBridge
from detectron2.config import get_cfg
from detectron2.engine import DefaultPredictor
from segmentation.msg import Prediction
from sensor_msgs.msg import Image
from torch import Tensor

if TYPE_CHECKING:
    from segmentation.detectron2.detectron2.config.config import CfgNode

AVAILABLE_MODELS = [
    "timm-efficientnet-b0",
    "timm-efficientnet-b3",
    "timm-efficientnet-b4",
    "timm-efficientnet-b7",
    "detectron",
]


class AbstractModel(ABC):
    r""" """

    @abstractmethod
    def get_class_names(
        self,
        index: Union[int, np.ndarray],
    ) -> Union[Tuple[str, ...], str]:
        ...

    @abstractmethod
    def full_output(
        self, x: Tensor
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Tuple[str, ...]]:
        ...


class EfficientNet:
    r""" """

    def __init__(self):
        pass


class DetectronModel(DefaultPredictor, AbstractModel):
    """Detectron Model interface"""

    def __init__(
        self,
        model_weights: str,
        config_file: str,
    ) -> None:
        self.config = self.setup_predictor_config(
            model_weights=model_weights,
            config_file=config_file,
        )
        super().__init__(self.config)

        self.class_names = self.metadata.class_names
        self.num_classes = len(self.class_names)

    def setup_predictor_config(
        self,
        model_weights: str,
        config_file: str,
    ) -> "CfgNode":
        """
        Setup config and return predictor. See config/defaults.py for more options
        """
        cfg = get_cfg()

        cfg.merge_from_file(config_file)
        cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.7
        # Mask R-CNN ResNet101 FPN weights
        cfg.MODEL.WEIGHTS = model_weights
        # This determines the resizing of the image. At 0, resizing is disabled.
        cfg.INPUT.MIN_SIZE_TEST = 0
        cfg.INPUT.FORMAT = "BGR"

        return cfg

    def forward(self, x: Tensor) -> dict:
        r"""Returns full detectron output

        Args:
            x (torch.Tensor): Input image

        Returns:
            dict: Detectron output, prediction masks + other information
        """
        return self.__call__(x)

    def get_class_names(
        self,
        index: np.ndarray,
    ) -> Union[Tuple[str, ...], str]:

        names = []
        for idx in index:
            names.append(self.class_names[idx])
        return tuple(names)

    def format_mask(
        self,
        mask: np.ndarray,
    ) -> np.ndarray:
        r"""Formats input mask to be sent over ROS publisher
        Args:
            mask (np.ndarray): Output from DefaultPredictor
        Returns:
            np.ndarray: mask compressed to shape (H, W, 1)

        Inputs:
            - **mask**: Has shape `(num_objects, H, W)`, where each image is 0's and 1's.

        Outputs:
            - np.uint8: New mask compressed to be (H, W, 1), where each different object found
            has it's unique integer
        """
        compressed_mask = np.zeros((mask.shape[1], mask.shape[2]), dtype=np.uint8)
        for i in range(len(mask)):
            compressed_mask += mask[i] * (i + 1)
        return compressed_mask

    def full_output(
        self, x: Tensor
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Tuple[str, ...]]:
        pred = self.forward(x)["instances"]
        centers = pred.pred_boxes.get_centers().cpu().numpy()
        mask = pred.pred_masks.cpu().numpy().astype(np.uint8)
        labels = self.get_class_names(pred.pred_classes)
        scores = pred.scores.cpu().numpy()

        return (mask, centers, labels, scores)


class SegmentationModel(nn.Module):
    def __init__(
        self,
        model_name: str,
        weights: str,
        rgb_topic: str,
        depth_topic: str,
        config_file: str,
    ) -> None:
        super(SegmentationModel, self).__init__()

        if model_name not in AVAILABLE_MODELS:
            raise ValueError("Input model not available, select one from list")

        # Create model
        # TODO: UPDATE timm model
        if model_name.find("timm") != -1:
            pass
        else:
            self.model = DetectronModel(model_weights=weights, config_file=config_file)

        self.pred_pub = rospy.Publisher("/seg/prediction", Prediction, queue_size=3)
        rgb_sub = message_filters.Subscriber(rgb_topic, Image)
        dep_sub = message_filters.Subscriber(depth_topic, Image)
        synch = message_filters.ApproximateTimeSynchronizer([rgb_sub, dep_sub], 3, 0.1)
        synch.registerCallback(self.callback)
        self.cv_bridge = CvBridge()

    def callback(
        self,
        rgb: Image,
        depth_map: Image,
    ) -> None:
        r"""ROS Subscriber to input RGB image + depth maps"""
        print(
            "SegmentationModel recieved message",
            rgb.header.stamp,
            depth_map.header.stamp,
        )
        rgb_img = self.cv_bridge.imgmsg_to_cv2(
            rgb,
            desired_encoding="passthrough",
        )

        (mask, centers, labels, scores) = self.model.full_output(rgb_img)

        pub_img = Prediction()
        pub_img.depth_map = depth_map
        pub_img.mask = mask.ravel().tobytes()
        pub_img.mask_height = mask.shape[2]
        pub_img.mask_width = mask.shape[1]
        pub_img.mask_channels = mask.shape[0]
        pub_img.header = rgb.header
        pub_img.scores = scores
        pub_img.centers = centers.ravel()
        pub_img.labels = labels

        #  end_t = time.perf_counter()
        #  print("TIME TAKEN SEG NODE: ", end_t - start_t)
        self.pred_pub.publish(pub_img)


if __name__ == "__main__":
    rospy.init_node("segmentation")
    weights = rospy.get_param("model_weights")
    model_type = rospy.get_param("segmentation_model")
    config = rospy.get_param("model_config")
    rgb_input_topic = rospy.get_param("rgb_input_topic")
    depth_input_topic = rospy.get_param("depth_input_topic")
    seg_model = SegmentationModel(
        model_name=model_type,
        weights=weights,
        config_file=config,
        rgb_topic=rgb_input_topic,
        depth_topic=depth_input_topic,
    )

    while not rospy.is_shutdown():
        rospy.spin()
