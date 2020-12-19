import cv2
import numpy as np

from utils import *

drawing = False
mode = True
rect = []


def draw_circle(event, x, y, flags, param):
    global rect, drawing

    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        rect = []
        rect.append(x)
        rect.append(y)
        rect.append(x)
        rect.append(y)

    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing:
            rect[2], rect[3] = x, y

    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        rect[2], rect[3] = x, y


cap = cv2.VideoCapture('./imgs/안주선가1.avi')

img = cv2.imread('./imgs/img8.jpg')
cv2.namedWindow('ori_image')
cv2.setMouseCallback('ori_image', draw_circle)

cv2.createTrackbar('min_thr', 'ori_image', 0, 255, lambda x : x)
cv2.setTrackbarPos('min_thr', 'ori_image', 255)

cv2.createTrackbar('min_thr2', 'ori_image', 0, 255, lambda x : x)
cv2.setTrackbarPos('min_thr2', 'ori_image', 172)
thresh = [127, 255]
add_radius = 5
add_inter_idx = 1

kernel = np.ones((3, 3), np.uint8)

img = cv2.resize(img, (640, 480))

while True:
    if not cap.isOpened():
        break

    ret, img = cap.read()
    if ret:
        img_draw = img.copy()

        min_thr = cv2.getTrackbarPos('min_thr', 'ori_image')
        thresh[0] = cv2.getTrackbarPos('min_thr2', 'ori_image')

        if rect:
            x1, y1, x2, y2 = rect
            if x1 != x2 and y1 != y2:
                cv2.rectangle(img_draw, (x1, y1), (x2, y2), (0, 255, 0), 2)
                img_roi = img[y1:y2, x1:x2]
                img_roi = cv2.cvtColor(img_roi, cv2.COLOR_BGR2GRAY)
                draw_roi = img_roi.copy()

                if not drawing:
                    ret, img_thresh = cv2.threshold(img_roi, min_thr, 255, cv2.THRESH_BINARY)

                    img_thresh = cv2.dilate(img_thresh, kernel, iterations=2)

                    draw_thresh = img_thresh.copy()
                    draw_thresh = cv2.cvtColor(draw_thresh, cv2.COLOR_GRAY2BGR)

                    # 반사광 채우기
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

                        l_val = int(img_roi[y][l_x])
                        r_val = int(img_roi[y][r_x])
                        draw_roi[y][x] = int((l_val + r_val) / 2)

                    # 동공 검출
                    draw_roi = cv2.cvtColor(draw_roi, cv2.COLOR_GRAY2BGR)
                    pupil_info, binary_eye = getPupil(draw_roi, thresh)

                    coord_mask = np.zeros((draw_roi.shape[0], draw_roi.shape[1]), np.uint8)
                    if pupil_info:
                        info = pupil_info[0]
                        x, y = info[0]
                        cv2.circle(draw_roi, (x, y), info[1] + add_radius, (255, 0, 0), 2)
                        cv2.circle(coord_mask, (x, y), info[1] + add_radius, 255, -1)

                        img_onlyeye = cv2.bitwise_and(binary_eye, coord_mask)

                        max_idx, max_val = 0, 0
                        for col_idx in range(img_onlyeye.shape[0]):
                            col_val = sum(img_onlyeye[col_idx])
                            if max_val < col_val:
                                max_idx = col_idx
                                max_val = col_val

                        l_row, r_row = 0, img_onlyeye.shape[1]
                        for row_idx in range(img_onlyeye.shape[1] - 1):
                            row_val = sum(img_onlyeye[:, row_idx])
                            if row_val != 0:
                                l_row = row_idx
                        for row_idx in range(img_onlyeye.shape[1] - 1, 0, -1):
                            row_val = sum(img_onlyeye[:, row_idx])
                            if row_val != 0:
                                r_row = row_idx

                        cv2.line(draw_roi, (l_row, max_idx), (r_row, max_idx), (0, 0, 255), 2)
                        cv2.putText(draw_roi, f'Pupil size : {max_val}', (20, 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (255 ,255, 255), 2, cv2.LINE_AA)

                    cv2.imshow('d', binary_eye)
                    # cv2.imshow('thresh', img_thresh)
                    # cv2.imshow('draw', draw_thresh)
                cv2.imshow('draw_roi', draw_roi)
        cv2.imshow('ori_image', img_draw)

        k = cv2.waitKey(1) & 0xFF
        if k == 27:
            break
    else:
        break

cv2.destroyAllWindows()
