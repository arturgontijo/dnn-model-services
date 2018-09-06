import numpy as np
import os
import time
import requests
import base64
import cv2
import traceback

resources_root = os.path.join("..", "..", "..", "CNTK", "Resources")


class ObjectDetector:
    def __init__(self, model, confidence, map_names, img_path):
        self.model = model
        self.confidence = confidence
        self.map_names = map_names
        self.img_path = img_path
        self.colors = []
        self.classes = []

    def detect(self):
        try:
            start_time = time.time()

            # Link
            if "http://" in self.img_path or "https://" in self.img_path:
                r = requests.get(self.img_path, allow_redirects=True)
                with open("temp_img.jpg", "wb") as my_f:
                    my_f.write(r.content)
                    self.img_path = "temp_img.jpg"

            # Base64
            elif len(self.img_path) > 500:
                imgdata = base64.b64decode(self.img_path)
                with open("temp_img.jpg", "wb") as f:
                    f.write(imgdata)
                    self.img_path = "temp_img.jpg"

            if self.model.upper() == "YOLOV3":
                model_file = os.path.join(resources_root, "Models", "yolov3.weights")
                model_config = os.path.join(resources_root, "Models", "yolov3.cfg")

            self.classes = [v for k, v in self.map_names.items()]
            self.colors = np.random.uniform(0, 255, size=(len(self.classes), 3))

            net = cv2.dnn.readNet(model_file, model_config)

            image = cv2.imread(self.img_path)

            w_image = image.shape[1]
            h_image = image.shape[0]
            scale = 0.00392

            blob = cv2.dnn.blobFromImage(
                image, scale, (416, 416), (0, 0, 0), True, crop=False
            )

            net.setInput(blob)

            outs = net.forward(self.get_output_layers(net))

            class_ids = []
            confidences = []
            boxes = []
            conf_threshold = 0.1
            nms_threshold = 0.4

            for out in outs:
                for detection in out:
                    scores = detection[5:]
                    class_id = np.argmax(scores)
                    confidence = scores[class_id]
                    if confidence >= float(self.confidence):
                        center_x = int(detection[0] * w_image)
                        center_y = int(detection[1] * h_image)
                        w = int(detection[2] * w_image)
                        h = int(detection[3] * h_image)
                        x = center_x - w / 2
                        y = center_y - h / 2
                        class_ids.append(class_id)
                        confidences.append(float(confidence))
                        boxes.append([x, y, w, h])

            indices = cv2.dnn.NMSBoxes(
                boxes, confidences, conf_threshold, nms_threshold
            )

            for i in indices:
                i = i[0]
                box = boxes[i]
                x = box[0]
                y = box[1]
                w = box[2]
                h = box[3]
                self.drawPred(
                    image,
                    class_ids[i],
                    confidences[i],
                    round(x),
                    round(y),
                    round(x + w),
                    round(y + h),
                )

            retval, buffer = cv2.imencode(".jpg", image)
            img_base64 = base64.b64encode(buffer)

            delta_time = time.time() - start_time

            if os.path.exists("temp_img.jpg"):
                os.remove("temp_img.jpg")

            return {
                "delta_time": "{:.4f}".format(delta_time),
                "img_base64": img_base64.decode("utf-8"),
            }

        except Exception as e:
            traceback.print_exc()
            return {"delta_time": "Fail", "img_base64": "Fail"}

    def get_output_layers(self, net):
        layer_names = net.getLayerNames()
        output_layers = [layer_names[i[0] - 1] for i in net.getUnconnectedOutLayers()]
        return output_layers

    def drawPred(self, image, classId, conf, left, top, right, bottom):
        label = "%.2f" % conf
        if self.map_names:
            assert classId < len(self.map_names)
            label = "%s:%s" % (self.map_names[classId], label)

        cv2.rectangle(image, (left, top), (right, bottom), self.colors[classId], 2)
        y = top - 15 if top - 15 > 15 else top + 15
        cv2.putText(
            image,
            label,
            (left, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            self.colors[classId],
            2,
        )
