from utils import *

import time

main_ui = uic.loadUiType('recording.ui')[0]
fourcc = cv2.VideoWriter_fourcc(*'DIVX')


class MyApp(QMainWindow, main_ui):
    def __init__(self):
        super(MyApp, self).__init__()
        # Window 초기화
        self.setupUi(self)
        self.initUI()

        # hyper parameter
        self.wait_rate = 1
        self.plot_limit = -150
        self.thresh = [180, 255]  # [min, max]

        # 변수 초기화 : PyQt
        self.clicked = False
        self.press_esc = False
        self.timerStep = 0

        # 변수 초기화 : OpenCV
        self.cam_num = 0
        self.cap = None
        self.display_img = False
        self.ori_img = None
        self.recording_time = 0
        self.roi_coord = []  # [x1, y1, x2, y2]
        self.horizontalSlider_max.setValue(self.thresh[1])
        self.horizontalSlider_min.setValue(self.thresh[0])
        self.label_maxThr.setText(f'{self.thresh[1]}')
        self.label_minThr.setText(f'{self.thresh[0]}')
        self.pupil_info = []

        # 녹화 변수
        self.recording = False
        self.saved_dir = ''
        self.saved_name = ''
        self.total_frame = 0
        self.record_frame_cnt = 0
        self.frame_out = None

        # 버튼에 기능 연결
        # self.pushButton_start.clicked.connect(self.startMeasurement)
        self.pushButton_cam.clicked.connect(self.camSetting_button)
        self.pushButton_startRecording.clicked.connect(self.startRecording_button)
        self.pushButton_selectDirectory.clicked.connect(self.selectDirectory_button)
        self.horizontalSlider_max.valueChanged.connect(self.maxThresh)
        self.horizontalSlider_min.valueChanged.connect(self.minThresh)
        self.comboBox_cam.currentIndexChanged.connect(self.camSetting_combo)

    def selectDirectory_button(self):
        self.saved_dir = QFileDialog.getExistingDirectory(self, 'Select save directory', 'C:/')
        self.label_saveDirectory.setText(self.saved_dir)

    def startRecording_button(self):
        self.recording_time = self.plainTextEdit_recording.toPlainText()
        self.recording_time = list(map(int, self.recording_time.split('.')))

        self.saved_name = self.plainTextEdit_name.toPlainText()
        self.saved_dir = self.label_saveDirectory.text()
        file_check = False
        if self.saved_dir:
            files = os.listdir(self.saved_dir)
            if f'{self.saved_name}.avi' not in files:
                file_check = True

        if self.recording_time and file_check:
            self.total_frame = self.recording_time[0] * 60 * 30
            self.total_frame += self.recording_time[1] * 30
            self.record_frame_cnt = 0
            print(f'{self.saved_dir}/{self.saved_name}.avi')
            self.frame_out = cv2.VideoWriter(f'{self.saved_dir}/{self.saved_name}.avi',
                                             fourcc,
                                             30.0,
                                             (640, 480))
            self.recording = True
        else:
            pass

    def camSetting_button(self):
        self.cap = cv2.VideoCapture(self.cam_num)

        if self.cap.isOpened():
            self.fig = plt.figure()
            self.plot_xs = []
            self.plot_ys = []
            self.max_y = 0

            self.startMeasurement()
        else:
            self.cap = None

    def camSetting_combo(self):
        self.cam_num = int(self.comboBox_cam.currentText())

    def startMeasurement(self):
        self.change_video = False
        if self.cap:
            num_of_frames = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)
            frame_cnt = 0
            while True:
                curTime = time.time()
                if self.press_esc or self.change_video or self.clicked:
                    break

                self.display_img, self.ori_img = self.cap.read()
                if self.display_img:
                    # idx_of_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
                    if self.roi_coord:
                        x1, y1, x2, y2 = self.roi_coord
                        height, width, _ = self.ori_img.shape
                        x1, y1, x2, y2 = int(x1 * width), int(y1 * height), int(x2 * width), int(y2 * height)
                        roi = self.ori_img[y1:y2, x1:x2].copy()
                    else:
                        roi = self.ori_img.copy()

                    # 동공 정보 (위치, 크기)
                    self.pupil_info, binary_eye = getPupil(roi, self.thresh)

                    # 속도 문제로 일단 폐지
                    # # sequence graph
                    # if self.pupil_info:
                    #     self.plot_ys.append(self.pupil_info[0][1])
                    # else:
                    #     self.plot_ys.append(0)
                    # # self.plot_xs.append(idx_of_frame)
                    # self.plot_xs.append(frame_cnt)
                    # self.plot_xs = self.plot_xs[self.plot_limit:]
                    # self.plot_ys = self.plot_ys[self.plot_limit:]
                    # graph = self.getGraph(self.plot_xs, self.plot_ys)
                    # graph = cv2.rotate(graph, cv2.ROTATE_90_CLOCKWISE)

                    if self.recording:
                        # self.ori_img 저장하면됨
                        self.frame_out.write(self.ori_img)
                        show_str = f'{frames_to_timecode(self.record_frame_cnt)}/{frames_to_timecode(self.total_frame)}'
                        self.label_recordTime.setText(show_str)
                        self.progressBar.setValue(int((self.record_frame_cnt / self.total_frame) * 100))
                        if self.record_frame_cnt == self.total_frame:
                            self.recording = False
                            self.frame_out.release()

                    self._showImage(self.ori_img, self.display_label)
                    self._showImage(binary_eye, self.display_binary)
                    # self._showImage(graph, self.display_graph)
                    # self.progressBar.setValue(int((idx_of_frame / num_of_frames) * 100))

                    frame_cnt += 1
                    self.record_frame_cnt += 1
                    cv2.waitKey(self.wait_rate)
                else:
                    break

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
            else:
                self.clicked = False
                self.roi_coord = []
                self.pupil_info = []

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

            self.pupil_info = []
            self._showImage(self.ori_img, self.display_label)

    def mouseReleaseEvent(self, event):
        if self.clicked:
            self.clicked = False
            self.fig = plt.figure()
            self.plot_xs = []
            self.plot_ys = []
            self.max_y = 0
            self.startMeasurement()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.press_esc = True
            self.close()

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
        self.comboBox_cam.addItem('0')
        self.comboBox_cam.addItem('1')
        self.comboBox_cam.addItem('2')
        self.comboBox_cam.addItem('3')
        self._center()
        self.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyApp()
    ex.show()
    sys.exit(app.exec_())
