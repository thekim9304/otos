import math
import cv2

img = cv2.imread('eyeimg.jpg')
scaling_factor = 0.7

img = cv2.resize(img, None, fx=scaling_factor, fy=scaling_factor, interpolation=cv2.INTER_AREA)
cv2.imshow('Input', img)
gray = cv2.cvtColor(~img, cv2.COLOR_BGR2GRAY)

ret, thresh_gray = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
cv2.imshow('Input', thresh_gray)
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
        img = cv2.drawContours(img, [contour], -1, (0, 255, 0), 1)
        cv2.circle(img, (int(x + radius), int(y + radius)), int(1 * radius), (0, 0, 255), -1)

cv2.imshow('Pupil Detector', img)
cv2.waitKey()
cv2.destroyAllWindows()


# 깃 테스트
