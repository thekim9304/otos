import cv2
import random
import numpy as np
import datetime as dt
import matplotlib.pyplot as plt

fig = plt.figure()
ax = fig.add_subplot(1, 1, 1)
xs = []
ys = []

for _ in range(1000):
    value = random.randrange(1, 100)

    xs.append(dt.datetime.now().strftime('%H:%M:%S.%f'))
    ys.append(value)

    xs = xs[-20:]
    ys = ys[-20:]

    ax.clear()
    ax.plot(xs, ys)

    plt.xticks(rotation=45, ha='right')
    plt.subplots_adjust(bottom=0.30)
    plt.title('test')
    plt.ylabel('random value')

    fig.canvas.draw()
    img = np.fromstring(fig.canvas.tostring_rgb(), dtype=np.uint8, sep='')
    img = img.reshape(fig.canvas.get_width_height()[::-1] + (3,))
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    cv2.imshow('plot', img)
    cv2.waitKey(30)


cv2.destroyAllWindows()
# plt.show()