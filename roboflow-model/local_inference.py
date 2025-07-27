from ultralytics import YOLO
import cv2


model = YOLO('weights.pt')

image_path = 'test_images_01.jpg'

results = model(image_path, conf=0.25)


annotated_image = results[0].plot()

cv2.imshow("Detection Result", annotated_image)

cv2.imwrite("detection_result.jpg", annotated_image)
print("Annotated image saved as 'detection_result.jpg'")


cv2.waitKey(0)
cv2.destroyAllWindows()