import cv2

video = cv2.VideoCapture('../RECORDS/25_02_2021/22_28_54.mkv')
fps = video.get(cv2.CAP_PROP_FPS)
print(fps)