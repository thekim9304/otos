
# 2.8mm == 더 가까움
# 2.1mm == 더 멈

from utils import *

import csv

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


'''
동공 검출 함수
'''


def getPupil(img, thresh):
    res = []

    gray = cv2.cvtColor(~img, cv2.COLOR_BGR2GRAY)
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
            res.append(((int(x + radius), int(y + radius)), int(1 * radius)))

    return res, thresh_gray


main_ui = uic.loadUiType('analysis.ui')[0]


class MyApp(QMainWindow, main_ui):
    def __init__(self):
        super(MyApp, self).__init__()
        # Window 초기화
        self.setupUi(self)
        self.initUI()

        # hyper parameter
        self.init_dir = './data'
        self.extensions = ['.avi', '.mp4']
        self.wait_rate = 1
        self.plot_limit = -150
        self.thresh = [180, 255]  # [min, max]

        # 변수 초기화 : PyQt
        self.video_paths = []
        self.display_video = ''
        self.change_video = False
        self.clicked = False
        self.press_esc = False
        self.timerStep = 0

        # 변수 초기화 : OpenCV
        self.cap = None
        self.display_img = False
        self.ori_img = None
        self.roi_coord = []  # [x1, y1, x2, y2]
        self.horizontalSlider_max.setValue(self.thresh[1])
        self.horizontalSlider_min.setValue(self.thresh[0])
        self.label_maxThr.setText(f'{self.thresh[1]}')
        self.label_minThr.setText(f'{self.thresh[0]}')
        self.pupil_info = []

        # 동공 크기 csv 저장 변수
        self.csv_file = None

        # 버튼에 기능 연결
        self.pushButton_GetFiles.clicked.connect(self.getFilesButton)
        self.pushButton_start.clicked.connect(self.startMeasurement)
        self.pushButton_saveDirectory.clicked.connect(self.selectDirectory_button)
        self.listWidget_video.itemDoubleClicked.connect(self.selectVideo)
        self.horizontalSlider_max.valueChanged.connect(self.maxThresh)
        self.horizontalSlider_min.valueChanged.connect(self.minThresh)

    def selectVideo(self):
        self.idx_video = self.listWidget_video.currentRow()
        self.cap = cv2.VideoCapture(self.video_paths[self.idx_video])
        self.display_img, self.ori_img = self.cap.read()
        if self.display_img:
            self.fig = plt.figure()
            self.plot_xs = []
            self.plot_ys = []
            self.max_y = 0
            self.roi_coord = []
            self.pupil_info = []
            self.clicked = False
            self.change_video = True
            self.csv_file = None
            self._showImage(self.ori_img, self.display_label)

    def startMeasurement(self):
        self.change_video = False
        csv_saveDir = self.label_saveDirectory.text()
        if self.cap and csv_saveDir:
            avi_filename = os.path.split(self.video_paths[self.idx_video])
            filename = os.path.splitext(avi_filename[-1])[0]

            self.csv_file = open(f'{csv_saveDir}/{filename}.csv', 'w', newline='')
            csvwriter = csv.writer(self.csv_file)
            csvwriter.writerow(['frame', 'pupil_size'])

            num_of_frames = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)
            while True:
                # if self.press_esc or self.change_video or self.clicked:
                if self.press_esc or self.change_video:
                    self.fig = plt.figure()
                    self.plot_xs = []
                    self.plot_ys = []
                    self.max_y = 0
                    self.roi_coord = []
                    self.pupil_info = []
                    self.clicked = False
                    self.change_video = True
                    self.csv_file = None
                    break

                self.display_img, self.ori_img = self.cap.read()
                if self.display_img:
                    idx_of_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)

                    if self.roi_coord:
                        x1, y1, x2, y2 = self.roi_coord
                        height, width, _ = self.ori_img.shape
                        x1, y1, x2, y2 = int(x1 * width), int(y1 * height), int(x2 * width), int(y2 * height)
                        roi = self.ori_img[y1:y2, x1:x2].copy()
                    else:
                        roi = self.ori_img.copy()

                    # 동공 정보 (위치, 크기)
                    self.pupil_info, binary_eye = getPupil(roi, self.thresh)

                    pupil_size = self.pupil_info[0][1] if self.pupil_info else 0

                    csvwriter.writerow([f'{idx_of_frame}', f'{pupil_size}'])

                    if self.checkBox_showGraph.isChecked():
                        # sequence graph
                        if self.pupil_info:
                            self.plot_ys.append(self.pupil_info[0][1])
                        else:
                            self.plot_ys.append(0)
                        self.plot_xs.append(idx_of_frame)
                        self.plot_xs = self.plot_xs[self.plot_limit:]
                        self.plot_ys = self.plot_ys[self.plot_limit:]
                        graph = self.getGraph(self.plot_xs, self.plot_ys)

                        self._showImage(graph, self.display_graph)
                    else:
                        self.plot_xs = []
                        self.plot_ys = []

                    show_str = f'{frames_to_timecode(idx_of_frame)}/{frames_to_timecode(num_of_frames)}'
                    self.label_videoTime.setText(show_str)

                    self._showImage(self.ori_img, self.display_label)
                    self._showImage(binary_eye, self.display_binary)
                    self.progressBar.setValue(int((idx_of_frame / num_of_frames) * 100))
                    cv2.waitKey(self.wait_rate)
                else:
                    break

            if not self.change_video:
                self.csv_file.close()

    def _showImage(self, img, display_label):
        if display_label is self.display_binary:
            draw_img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        elif display_label is self.display_label:
            draw_img = img.copy()
            height, width, _ = img.shape

            if self.roi_coord:
                x1, y1, x2, y2 = self.roi_coord
                draw_img = cv2.rectangle(draw_img,
                                         (int(x1 * width), int(y1 * height)),
                                         (int(x2 * width), int(y2 * height)),
                                         (0, 0, 255), 2)
            if self.pupil_info:
                for info in self.pupil_info[:1]:
                    x, y = info[0]
                    if self.roi_coord:
                        x, y = int(x + self.roi_coord[0] * width), int(y + self.roi_coord[1] * height)
                    cv2.circle(draw_img, (x, y), info[1], (255, 0, 0), -1)
        else:
            draw_img = img.copy()

        qpixmap = cvtPixmap(draw_img, (display_label.width(), display_label.height()))
        display_label.setPixmap(qpixmap)

    def mousePressEvent(self, event):
        if self.display_img:
            rel_x = (event.x() - self.display_label.x()) / self.display_label.width()
            rel_y = (event.y() - self.display_label.y()) / self.display_label.height()

            if 0 <= rel_x <= 1 and 0 <= rel_y < 1:
                self.clicked = True
                self.roi_coord = [rel_x, rel_y, rel_x, rel_y]
            # else:
            #     self.clicked = False
            #     self.roi_coord = []
            #     self.pupil_info = []

            self._showImage(self.ori_img, self.display_label)

    def mouseMoveEvent(self, event):
        if self.display_img and self.clicked:
            rel_x = (event.x() - self.display_label.x()) / self.display_label.width()
            rel_y = (event.y() - self.display_label.y()) / self.display_label.height()

            if 0 <= rel_x <= 1 and 0 <= rel_y < 1:
                self.roi_coord[2] = rel_x
                self.roi_coord[3] = rel_y
            elif rel_x > 1:
                self.roi_coord[2] = 1
            elif rel_y > 1:
                self.roi_coord[3] = 1
            elif rel_x < 0:
                self.roi_coord[2] = 0
            elif rel_y < 0:
                self.roi_coord[3] = 0

            self._showImage(self.ori_img, self.display_label)

    def mouseReleaseEvent(self, event):
        if self.clicked:
            self.clicked = False

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.press_esc = True
            self.close()

    def selectDirectory_button(self):
        self.saved_dir = QFileDialog.getExistingDirectory(self, 'Select save directory', './')
        self.label_saveDirectory.setText(self.saved_dir)

    def getFilesButton(self):
        self.video_paths = []
        self.video_paths = QFileDialog.getOpenFileNames(self, 'Get Files', self.init_dir)[0]
        if self.video_paths:
            temp = []
            for i, path in enumerate(self.video_paths):
                if os.path.splitext(path)[-1] in self.extensions:
                    temp.append(path)
            self.video_paths = temp

            for i, path in enumerate(self.video_paths):
                self.listWidget_video.insertItem(i, os.path.basename(path))
        else:
            self.listWidget_video.clear()

    def maxThresh(self):
        self.thresh[1] = self.horizontalSlider_max.value()
        if self.thresh[1] <= self.thresh[0]:
            self.thresh[1] = self.thresh[0] + 1
        self.horizontalSlider_max.setValue(self.thresh[1])
        self.label_maxThr.setText(f'{self.thresh[1]}')

    def minThresh(self):
        self.thresh[0] = self.horizontalSlider_min.value()
        if self.thresh[0] >= self.thresh[1]:
            self.thresh[0] = self.thresh[1] - 1
        self.horizontalSlider_min.setValue(self.thresh[0])
        self.label_minThr.setText(f'{self.thresh[0]}')

    def getGraph(self, xs, ys):
        max_y = max(ys)
        if self.max_y < max_y:
            self.max_y = max_y

        ax = self.fig.add_subplot(1, 1, 1)

        ax.clear()
        ax.plot(xs, ys)
        plt.ylim(-1, self.max_y + 10)
        plt.xticks(rotation=45, ha='right')
        plt.ylabel('Pupil size')

        self.fig.canvas.draw()
        img = np.fromstring(self.fig.canvas.tostring_rgb(), dtype=np.uint8, sep='')
        img = img.reshape(self.fig.canvas.get_width_height()[::-1] + (3,))
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        return img

    def _center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def initUI(self):
        self.setWindowTitle('Visual fatigue measurement')
        self.setWindowIcon(QIcon('icon.jpg'))
        self._center()
        self.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyApp()
    ex.show()
    sys.exit(app.exec_())
