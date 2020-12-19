# pyinstaller -w -F --icon=./graph2.ico analysis.py

# 2.8mm == 더 가까움
# 2.1mm == 더 멈

from utils import *

import csv


main_ui = uic.loadUiType('get_pupil_size.ui')[0]


class MyApp(QMainWindow, main_ui):
    def __init__(self):
        super(MyApp, self).__init__()
        # Window 초기화
        self.setupUi(self)
        self.initUI()

        # hyper parameter
        self.init_dir = './'
        self.extensions = ['.avi', '.mp4']
        self.wait_rate = 1
        self.plot_limit = 150
        self.thresh = [180, 255]  # [min, max]
        self.ref_thresh = 255
        self.add_radius = 10

        # 변수 초기화 : PyQt
        self.video_paths = []
        self.display_video = ''
        self.change_video = False
        self.clicked = False
        self.clicked_start = False
        self.clicked_save_csv = False
        self.press_esc = False
        self.timerStep = 0

        # 변수 초기화 : OpenCV
        self.cap = None
        self.display_img = False
        self.ori_img = None
        self.roi_coord = []  # [x1, y1, x2, y2]
        self.horizontalSlider_max.setValue(self.thresh[1])
        self.horizontalSlider_min.setValue(self.thresh[0])
        self.horizontalSlider_reflection_min.setValue(self.ref_thresh)
        self.label_reflection_min.setText(f'{self.ref_thresh}')
        self.label_maxThr.setText(f'{self.thresh[1]}')
        self.label_minThr.setText(f'{self.thresh[0]}')
        self.pupil_info = []
        self.change_frame = False
        self.total_frames = 0

        # 동공 크기 csv 저장 변수
        self.csv_file = None
        self.plot_xs = []
        self.plot_ys = []

        # 버튼에 기능 연결
        self.pushButton_GetFiles.clicked.connect(self.getFilesButton)
        # self.pushButton_start.clicked.connect(self.startMeasurement)
        self.pushButton_saveDirectory.clicked.connect(self.selectDirectory_button)
        self.pushButton_csvSave.clicked.connect(self.save_csv)
        self.pushButton_quit.clicked.connect(self.program_quit)
        self.listWidget_video.itemDoubleClicked.connect(self.selectVideo)
        self.horizontalSlider_max.valueChanged.connect(self.maxThresh)
        self.horizontalSlider_min.valueChanged.connect(self.minThresh)
        self.horizontalSlider_reflection_min.valueChanged.connect(self.refThresh)
        self.horizontalSlider_video.sliderMoved.connect(self.video_frame)
        self.horizontalSlider_video.valueChanged.connect(self.video_frame_keyboard)

    def save_csv(self):
        self.clicked_save_csv = True

        csv_saveDir = self.label_saveDirectory.text()
        save_name = self.plainTextEdit_csvName.toPlainText()
        print(save_name)
        self.csv_file = open(f'{csv_saveDir}/{save_name}.csv', 'w', newline='')
        csvwriter = csv.writer(self.csv_file)
        csvwriter.writerow(['frame', 'pupil_size'])

        for xs, ys in zip(self.plot_xs, self.plot_ys):
            csvwriter.writerow([f'{xs}', f'{ys}'])

        self.csv_file.close()

    def video_frame_keyboard(self):
        if not self.change_frame:
            pass
        else:
            self.video_frame()

    def video_frame(self):
        self.change_frame = True

        frame_idx = self.horizontalSlider_video.value()
        show_str = f'{frames_to_timecode(frame_idx)}/{frames_to_timecode(self.total_frames)}'
        self.label_videoTime.setText(show_str)
        self.label_videoFrame.setText(f'{frame_idx}/{self.total_frames}')

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        self.display_img, self.ori_img = self.cap.read()
        self._showImage(self.ori_img, self.display_label, True)
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)

        s_idx = frame_idx - self.plot_limit
        s_idx = 0 if s_idx < 0 else s_idx
        e_idx = frame_idx + self.plot_limit
        e_idx = -1 if e_idx > self.total_frames else e_idx
        show_xs = self.plot_xs[s_idx: e_idx]
        show_ys = self.plot_ys[s_idx: e_idx]
        graph = self.getGraph(show_xs, show_ys, frame_idx)

        self._showImage(graph, self.display_graph)

    def startMeasurement(self):
        self.clicked_start = True
        self.change_video = False
        csv_saveDir = self.label_saveDirectory.text()
        if self.cap and csv_saveDir:
            while True:
                # if self.press_esc or self.change_video or self.clicked:
                if self.press_esc or self.change_video or self.clicked_save_csv:
                    self.fig = plt.figure()
                    # self.plot_xs = []
                    # self.plot_ys = []
                    self.max_y = 0
                    self.roi_coord = []
                    self.pupil_info = []
                    self.clicked = False
                    self.clicked_save_csv = False
                    self.change_video = True
                    self.csv_file = None
                    break

                self.display_img, self.ori_img = self.cap.read()

                if self.display_img and not self.change_frame:
                    idx_of_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                    x1, x2, y1, y2 = 0, 0, 0, 0

                    if self.roi_coord and not self.clicked:
                        x1, y1, x2, y2 = self.roi_coord
                        height, width, _ = self.ori_img.shape
                        x1, y1, x2, y2 = int(x1 * width), int(y1 * height), int(x2 * width), int(y2 * height)
                        roi = self.ori_img[y1:y2, x1:x2].copy()
                    else:
                        roi = self.ori_img.copy()

                    # 반사광 제거
                    roi = fill_reflected_light(roi, self.ref_thresh)
                    if self.roi_coord:
                        roi = cv2.cvtColor(roi, cv2.COLOR_GRAY2BGR)
                        self.ori_img[y1:y2, x1:x2] = roi
                    else:
                        self.ori_img = cv2.cvtColor(roi, cv2.COLOR_GRAY2BGR)
                    # 동공 정보 (위치, 크기)
                    self.pupil_info, binary_eye = getPupil(roi, self.thresh)

                    # 동공 크기 값 측정
                    if self.pupil_info:
                        self.plot_ys[idx_of_frame] = self.pupil_info[0][1]

                        # coord_mask = np.zeros((roi.shape[0], roi.shape[1]), np.uint8)
                        # info = self.pupil_info[0]
                        # x, y = info[0]
                        # cv2.circle(coord_mask, (x, y), info[1] + self.add_radius, 255, -1)
                        #
                        # img_eye_only = cv2.bitwise_and(binary_eye, coord_mask)
                        #
                        # max_idx, max_val = 0, 0
                        # for col_idx in range(img_eye_only.shape[0]):
                        #     col_val = sum(img_eye_only[col_idx])
                        #     if max_val < col_val:
                        #         max_idx = col_idx
                        #         max_val = col_val
                        #
                        # l_row, r_row = 0, img_eye_only.shape[1]
                        # for row_idx in range(img_eye_only.shape[1] - 1):
                        #     row_val = sum(img_eye_only[:, row_idx])
                        #     if row_val != 0:
                        #         l_row = row_idx
                        # for row_idx in range(img_eye_only.shape[1] - 1, 0, -1):
                        #     row_val = sum(img_eye_only[:, row_idx])
                        #     if row_val != 0:
                        #         r_row = row_idx
                        #
                        # cv2.line(roi, (l_row, max_idx), (r_row, max_idx), (0, 0, 255), 2)
                        # self.ori_img[y1:y2, x1:x2] = roi
                    else:
                        self.plot_ys[idx_of_frame] = 0

                    if self.checkBox_showGraph.isChecked():
                        # sequence graph
                        # idx_of_frame`
                        s_idx = idx_of_frame - self.plot_limit
                        s_idx = 0 if s_idx < 0 else s_idx
                        e_idx = idx_of_frame + self.plot_limit
                        e_idx = -1 if e_idx > self.total_frames else e_idx
                        show_xs = self.plot_xs[s_idx: e_idx]
                        show_ys = self.plot_ys[s_idx: e_idx]
                        graph = self.getGraph(show_xs, show_ys, idx_of_frame)

                        self._showImage(graph, self.display_graph)

                    show_str = f'{frames_to_timecode(idx_of_frame)}/{frames_to_timecode(self.total_frames)}'
                    self.label_videoTime.setText(show_str)
                    self.label_videoFrame.setText(f'{idx_of_frame}/{self.total_frames}')
                    self._showImage(self.ori_img, self.display_label)
                    self._showImage(binary_eye, self.display_binary)

                    self.horizontalSlider_video.setValue(idx_of_frame)
                    cv2.waitKey(self.wait_rate)
                elif self.display_img:
                    break
                else:
                    break

        self.clicked_start = False

    def _showImage(self, img, display_label, slide=False):
        if display_label is self.display_binary:
            draw_img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        elif display_label is self.display_label and slide:
            draw_img = img.copy()
            height, width, _ = img.shape
            if self.roi_coord:
                x1, y1, x2, y2 = self.roi_coord
                draw_img = cv2.rectangle(draw_img,
                                         (int(x1 * width), int(y1 * height)),
                                         (int(x2 * width), int(y2 * height)),
                                         (0, 0, 255), 2)
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
                    cv2.circle(draw_img, (x, y), info[1] + self.add_radius, (255, 0, 0), 2)
        else:
            draw_img = img.copy()

        qpixmap = cvtPixmap(draw_img, (display_label.width(), display_label.height()))
        display_label.setPixmap(qpixmap)

    def selectVideo(self):
        self.idx_video = self.listWidget_video.currentRow()
        self.cap = cv2.VideoCapture(self.video_paths[self.idx_video])
        self.display_img, self.ori_img = self.cap.read()
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        if self.display_img:
            self.fig = plt.figure()
            self.max_y = 0
            self.roi_coord = []
            self.pupil_info = []
            self.clicked = False
            self.change_video = True
            self.csv_file = None
            self.change_frame = True
            self.clicked_save_csv = False
            avi_filename = os.path.split(self.video_paths[self.idx_video])
            filename = os.path.splitext(avi_filename[-1])[0]
            self.plainTextEdit_csvName.setPlainText(filename)
            self.total_frames = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)
            self.plot_xs = list(range(int(self.total_frames)))
            self.plot_ys = [0] * int(self.total_frames)
            self.horizontalSlider_video.setRange(0, self.total_frames)
            self._showImage(self.ori_img, self.display_label)

    def mousePressEvent(self, event):
        if self.display_img:
            rel_x = (event.x() - self.display_label.x()) / self.display_label.width()
            rel_y = (event.y() - self.display_label.y()) / self.display_label.height()

            if 0 <= rel_x <= 1 and 0 <= rel_y < 1:
                self.clicked = True
                self.roi_coord = [rel_x, rel_y, rel_x, rel_y]

            self._showImage(self.ori_img, self.display_label, slide=True)

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

            self._showImage(self.ori_img, self.display_label, slide=True)

    def mouseReleaseEvent(self, event):
        if  self.clicked:
            self.clicked = False

            x1, y1, x2, y2 = self.roi_coord
            if x1 == x2 or y1 == y2:
                self.roi_coord = []
            else:
                if x1 > x2:
                    self.roi_coord[2] = x1
                    self.roi_coord[0] = x2
                if y1 > y2:
                    self.roi_coord[3] = y1
                    self.roi_coord[1] = y2

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.press_esc = True
            self.close()
        elif e.key() == Qt.Key_Space:
            self.clicked_start = True
            if not self.change_frame:
                self.change_frame = True
            else:
                self.change_frame = False
                self.startMeasurement()

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

    def refThresh(self):
        x1, y1, x2, y2 = 0, 0, 0, 0

        self.ref_thresh = self.horizontalSlider_reflection_min.value()
        self.label_reflection_min.setText(f'{self.ref_thresh}')

        if self.cap and not self.clicked_start:
            post_img = self.ori_img.copy()

            if self.roi_coord and not self.clicked:
                x1, y1, x2, y2 = self.roi_coord
                height, width, _ = self.ori_img.shape
                x1, y1, x2, y2 = int(x1 * width), int(y1 * height), int(x2 * width), int(y2 * height)
                roi = self.ori_img[y1:y2, x1:x2].copy()
            else:
                roi = self.ori_img.copy()

            roi = fill_reflected_light(roi, self.ref_thresh)
            if self.roi_coord:
                roi = cv2.cvtColor(roi, cv2.COLOR_GRAY2BGR)
                post_img[y1:y2, x1:x2] = roi
            else:
                post_img = cv2.cvtColor(roi, cv2.COLOR_GRAY2BGR)
            self.pupil_info, binary_eye = getPupil(roi, self.thresh)

            self._showImage(post_img, self.display_label)
            self._showImage(binary_eye, self.display_binary)


    def maxThresh(self):
        x1, y1, x2, y2 = 0, 0, 0, 0

        self.thresh[1] = self.horizontalSlider_max.value()
        if self.thresh[1] <= self.thresh[0]:
            self.thresh[1] = self.thresh[0] + 1
        self.horizontalSlider_max.setValue(self.thresh[1])
        self.label_maxThr.setText(f'{self.thresh[1]}')

        if self.cap and not self.clicked_start:
            post_img = self.ori_img.copy()

            if self.roi_coord and not self.clicked:
                x1, y1, x2, y2 = self.roi_coord
                height, width, _ = self.ori_img.shape
                x1, y1, x2, y2 = int(x1 * width), int(y1 * height), int(x2 * width), int(y2 * height)
                roi = self.ori_img[y1:y2, x1:x2].copy()
            else:
                roi = self.ori_img.copy()

            roi = fill_reflected_light(roi, self.ref_thresh)
            if self.roi_coord:
                roi = cv2.cvtColor(roi, cv2.COLOR_GRAY2BGR)
                post_img[y1:y2, x1:x2] = roi
            else:
                post_img = cv2.cvtColor(roi, cv2.COLOR_GRAY2BGR)
            self.pupil_info, binary_eye = getPupil(roi, self.thresh)

            self._showImage(post_img, self.display_label)
            self._showImage(binary_eye, self.display_binary)

    def minThresh(self):
        x1, y1, x2, y2 = 0, 0, 0, 0

        self.thresh[0] = self.horizontalSlider_min.value()
        if self.thresh[0] >= self.thresh[1]:
            self.thresh[0] = self.thresh[1] - 1
        self.horizontalSlider_min.setValue(self.thresh[0])
        self.label_minThr.setText(f'{self.thresh[0]}')

        if self.cap and not self.clicked_start:
            post_img = self.ori_img.copy()

            if self.roi_coord and not self.clicked:
                x1, y1, x2, y2 = self.roi_coord
                height, width, _ = self.ori_img.shape
                x1, y1, x2, y2 = int(x1 * width), int(y1 * height), int(x2 * width), int(y2 * height)
                roi = self.ori_img[y1:y2, x1:x2].copy()
            else:
                roi = self.ori_img.copy()

            roi = fill_reflected_light(roi, self.ref_thresh)
            if self.roi_coord:
                roi = cv2.cvtColor(roi, cv2.COLOR_GRAY2BGR)
                post_img[y1:y2, x1:x2] = roi
            else:
                post_img = cv2.cvtColor(roi, cv2.COLOR_GRAY2BGR)
            self.pupil_info, binary_eye = getPupil(roi, self.thresh)

            self._showImage(post_img, self.display_label)
            self._showImage(binary_eye, self.display_binary)

    def getGraph(self, xs, ys, pre_idx):
        max_y = max(ys)
        if self.max_y < max_y:
            self.max_y = max_y

        ax = self.fig.add_subplot(1, 1, 1)

        ax.clear()
        ax.plot(xs, ys)
        plt.scatter(pre_idx, max_y + 8, marker='o', color='salmon')
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
        self.setFixedSize(1198, 746)
        self._center()
        self.show()

    def program_quit(self):
        self.press_esc = True
        QCoreApplication.instance().quit()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyApp()
    ex.show()
    sys.exit(app.exec_())
