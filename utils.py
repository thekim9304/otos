import os
import cv2
import sys
import math
import time
import numpy as np
import matplotlib.pyplot as plt

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import uic


def cvtPixmap(frame, img_size):
    frame = cv2.resize(frame, img_size)
    height, width, channel = frame.shape
    bytesPerLine = 3 * width
    qImg = QImage(frame.data,
                  width,
                  height,
                  bytesPerLine,
                  QImage.Format_RGB888).rgbSwapped()
    qpixmap = QPixmap.fromImage(qImg)

    return qpixmap


def fill_reflected_light(ori_img, min_thr, iteration=2, add_inter_idx=1):
    if len(ori_img.shape) == 3:
        ori_img = cv2.cvtColor(ori_img, cv2.COLOR_BGR2GRAY)

    ret, img_thresh = cv2.threshold(ori_img, min_thr, 255, cv2.THRESH_BINARY)

    kernel = np.ones((3, 3), np.uint8)
    img_thresh = cv2.dilate(img_thresh, kernel, iterations=iteration)

    draw_img = ori_img.copy()

    reflection_points = np.where(img_thresh == 255)

    for y, x in zip(reflection_points[0], reflection_points[1]):
        l_x, r_x = x - 1, x + 1
        l_x = l_x if l_x >= 0 else 0
        r_x = r_x if r_x < img_thresh.shape[1] else img_thresh.shape[1] - 1

        while l_x >= 0 and img_thresh[y][l_x] == 255:
            l_x -= 1
        while r_x < (img_thresh.shape[1] - 1) and img_thresh[y][r_x] == 255:
            r_x += 1

        l_x -= add_inter_idx
        r_x += add_inter_idx
        l_x = l_x if l_x >= 0 else 0
        r_x = r_x if r_x < img_thresh.shape[1] else img_thresh.shape[1] - 1

        l_val = int(ori_img[y][l_x])
        r_val = int(ori_img[y][r_x])
        draw_img[y][x] = int((l_val + r_val) / 2)

    return draw_img


def getPupil(img, thresh):
    res = []

    if len(img.shape) == 3:
        gray = cv2.cvtColor(~img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    ret, thresh_gray = cv2.threshold(gray, thresh[0], thresh[1], cv2.THRESH_BINARY)
    contours, hierarchy = cv2.findContours(thresh_gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    for contour in contours:
        area = cv2.contourArea(contour)
        rect = cv2.boundingRect(contour)
        x, y, width, height = rect
        radius = 0.25 * (width + height)

        area_condition = (100 <= area)
        symmetry_condition = (abs(1 - float(width) / float(height)) <= 0.2)
        fill_condition = (abs(1 - (area / (math.pi * math.pow(radius, 2.0)))) <= 0.3)

        if area_condition and symmetry_condition and fill_condition:
            res.append(((int(x + radius), int(y + radius)), int(1 * radius), rect))

    return res, thresh_gray


def frames_to_timecode(total_frames, frame_rate=30, drop=False):
    """
    Method that converts frames to SMPTE timecode.

    :param total_frames: Number of frames
    :param frame_rate: frames per second
    :param drop: true if time code should drop frames, false if not
    :returns: SMPTE timecode as string, e.g. '01:02:12:32' or '01:02:12;32'
    """
    if drop and frame_rate not in [29.97, 59.94]:
        raise NotImplementedError("Time code calculation logic only supports drop frame "
                                  "calculations for 29.97 and 59.94 fps.")

    # for a good discussion around time codes and sample code, see
    # http://andrewduncan.net/timecodes/

    # round fps to the nearest integer
    # note that for frame rates such as 29.97 or 59.94,
    # we treat them as 30 and 60 when converting to time code
    # then, in some cases we 'compensate' by adding 'drop frames',
    # e.g. jump in the time code at certain points to make sure that
    # the time code calculations are roughly right.
    #
    # for a good explanation, see
    # https://documentation.apple.com/en/finalcutpro/usermanual/index.html#chapter=D%26section=6
    fps_int = int(round(frame_rate))

    if drop:
        # drop-frame-mode
        # add two 'fake' frames every minute but not every 10 minutes
        #
        # example at the one minute mark:
        #
        # frame: 1795 non-drop: 00:00:59:25 drop: 00:00:59;25
        # frame: 1796 non-drop: 00:00:59:26 drop: 00:00:59;26
        # frame: 1797 non-drop: 00:00:59:27 drop: 00:00:59;27
        # frame: 1798 non-drop: 00:00:59:28 drop: 00:00:59;28
        # frame: 1799 non-drop: 00:00:59:29 drop: 00:00:59;29
        # frame: 1800 non-drop: 00:01:00:00 drop: 00:01:00;02
        # frame: 1801 non-drop: 00:01:00:01 drop: 00:01:00;03
        # frame: 1802 non-drop: 00:01:00:02 drop: 00:01:00;04
        # frame: 1803 non-drop: 00:01:00:03 drop: 00:01:00;05
        # frame: 1804 non-drop: 00:01:00:04 drop: 00:01:00;06
        # frame: 1805 non-drop: 00:01:00:05 drop: 00:01:00;07
        #
        # example at the ten minute mark:
        #
        # frame: 17977 non-drop: 00:09:59:07 drop: 00:09:59;25
        # frame: 17978 non-drop: 00:09:59:08 drop: 00:09:59;26
        # frame: 17979 non-drop: 00:09:59:09 drop: 00:09:59;27
        # frame: 17980 non-drop: 00:09:59:10 drop: 00:09:59;28
        # frame: 17981 non-drop: 00:09:59:11 drop: 00:09:59;29
        # frame: 17982 non-drop: 00:09:59:12 drop: 00:10:00;00
        # frame: 17983 non-drop: 00:09:59:13 drop: 00:10:00;01
        # frame: 17984 non-drop: 00:09:59:14 drop: 00:10:00;02
        # frame: 17985 non-drop: 00:09:59:15 drop: 00:10:00;03
        # frame: 17986 non-drop: 00:09:59:16 drop: 00:10:00;04
        # frame: 17987 non-drop: 00:09:59:17 drop: 00:10:00;05

        # calculate number of drop frames for a 29.97 std NTSC
        # workflow. Here there are 30*60 = 1800 frames in one
        # minute

        FRAMES_IN_ONE_MINUTE = 1800 - 2

        FRAMES_IN_TEN_MINUTES = (FRAMES_IN_ONE_MINUTE * 10) - 2

        ten_minute_chunks = total_frames / FRAMES_IN_TEN_MINUTES
        one_minute_chunks = total_frames % FRAMES_IN_TEN_MINUTES

        ten_minute_part = 18 * ten_minute_chunks
        one_minute_part = 2 * ((one_minute_chunks - 2) / FRAMES_IN_ONE_MINUTE)

        if one_minute_part < 0:
            one_minute_part = 0

        # add extra frames
        total_frames += ten_minute_part + one_minute_part

        # for 60 fps drop frame calculations, we add twice the number of frames
        if fps_int == 60:
            total_frames = total_frames * 2

        # time codes are on the form 12:12:12;12
        smpte_token = ";"

    else:
        # time codes are on the form 12:12:12:12
        smpte_token = ":"

    # now split our frames into time code
    hours = int(total_frames / (3600 * fps_int))
    minutes = int(total_frames / (60 * fps_int) % 60)
    seconds = int(total_frames / fps_int % 60)
    frames = int(total_frames % fps_int)
    return "%02d:%02d:%02d%s%02d" % (hours, minutes, seconds, smpte_token, frames)
