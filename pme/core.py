import os
import threading
import logging
import time
import sys
import csv

from datetime import datetime
from collections import deque

import cv2
import numpy as np

from IPython.display import display, Image, clear_output
import ipywidgets

from .utils import OutputWidgetHandler, wrapper


class GUI:
    def __init__(self, pipeline_func=None, mode="stream", output_directory=None, camera_id=None, sanity_check_image=None):
        
        self.mode = mode
        self.image = np.zeros(shape=(100, 200, 3),
                              dtype=np.uint8)  # initial image. will be overrided by the sanity image and finally camera input.
        self.images = None  # processed images
        self.pipeline_func = pipeline_func
        self.camera_id = camera_id
        self.pipeline_func = pipeline_func
        self.black = np.zeros((1, 1, 3), dtype=np.uint8)
        self.path = os.path.join(os.getcwd(), "data")
        
        
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        print("- images will be saved to %s" % self.path)
        
        
        if self.mode == "stream":  # initialization process
            print("- running as camera streaming mode")

            self.processed_image_widgets = {}

            if self.pipeline_func:
                #print("- sanity checking pipeline_func")
                if sanity_check_image:
                    self.image = sanity_check_image
                    assert_image_format(self.image)

                self.images, self.csv_logs, self.stream_logs = wrapper(
                    self.pipeline_func, self.image)
                
                if self.csv_logs is not None:
                    self.csv_path = os.path.join(self.path,"result.csv")
                    with open(self.csv_path, "a") as f:
                        pass
                    print("- csv_logs will be appended to %s" % self.csv_path)
                    
                self.layout = {'width': str(
                    80/len(self.images))+"%", 'height': '1px', 'border': '1px solid black'}
                for i in range(len(self.images)):
                    self.processed_image_widgets[str(i)] = ipywidgets.Image(
                        format='jpeg', value=bytes(cv2.imencode('.jpg', self.image)[1]), layout=self.layout)

            assert self.camera_id is not None, "must specify a camera number for camera streaming"

            # assert video device is closed
            cv2.VideoCapture(self.camera_id).release()
            self.camera = cv2.VideoCapture(self.camera_id)
            self.camera.set(cv2.CAP_PROP_FOURCC,
                            cv2.VideoWriter_fourcc(*"MJPG"))
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            assert self.camera.isOpened(
            ), "problem with establishing connection with camera. ex. camera_id=0"
            self.camera.release()
            #print("\t- camera properly recognized")

            # fps
            self.fps = 0
            self.n_frame = 3
            self.q = deque([time.time() for i in range(self.n_frame)])

            # logging including csv logging
            self.logger = logging.getLogger("default logger")
            self.handler = OutputWidgetHandler()  # handler.out is the ipywidgets.Textarea
            self.handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(message)s'))
            self.logger.addHandler(self.handler)
            self.logger.setLevel(logging.INFO)

    def stream(self):
        def capture(_):
            
            
            base = datetime.now().strftime("%Y%m%d_%H%M%S")
            basefile = base + ".jpg"
            orig_file = os.path.join(self.path, basefile)
            cv2.imwrite(orig_file, self.image)
            
            if self.csv_logs is not None:
                s = []
                
                for line in self.csv_logs:
                    s.append([base, line])
                with open(self.csv_path, "a") as f:
                    writer = csv.writer(f, lineterminator='\n')
                    if isinstance(s[0], list):
                        writer.writerows(s)
                    else:
                        writer.writerow(s)
                self.logger.info("csv logged as %s" % s)
            
            self.logger.info("input image saved as %s." % base)

            if self.images is not None and self.image_analysis_widget.value == True:
                for i, image in enumerate(self.images):
                    _base = base + "__"+str(i)+".jpg"
                    processed_file = os.path.join(
                        self.path, _base)
                    cv2.imwrite(os.path.join(self.path, processed_file), image)
                    self.logger.info(
                        "processed image saved as %s" % _base)

        def live(*args):
            while self.state_widget.value == 'connect':
                _, self.image = self.camera.read()

                # calculate fps
                now = time.time()
                self.fps = self.n_frame / (now - self.q.popleft())
                self.q.append(now)
                self.fps_widget.value = "fps: " + str(self.fps)
                self.acquire_image_widget.on_click(capture)

                if self.image is not None:
                    if self.hide_input_widget.value == False:
                        self.image_widget.layout = {
                            'width': "80%", 'border': '1px solid black'}
                        self.image_widget.value = bytes(cv2.imencode(
                            '.jpg', self.image)[1])  # original input
                    else:
                        self.image_widget.layout = {
                            'width': "80%", 'height': '1px', 'border': '1px solid black'}
                        self.image_widget.value = bytes(cv2.imencode(
                            '.jpg', self.black)[1])  # original input

                    if self.pipeline_func is not None:
                        # apply pipeline and visualize processed images only when the analysis checkbox is ticked
                        if self.image_analysis_widget.value:
                            self.images, self.csv_logs, self.stream_logs = wrapper(
                                self.pipeline_func, self.image)
                            for i, image in enumerate(self.images):
                                self.processed_image_widgets[str(i)].value = bytes(
                                    cv2.imencode('.jpg', image)[1])
                                self.processed_image_widgets[str(i)].layout = {'width': str(
                                    80/len(self.images))+"%", 'border': '1px solid black'}
                                
                        else:  # if checkbox is unticked, force the height of the layout to 1px and hide
                            if self.processed_image_widgets["0"].value != bytes(cv2.imencode('.jpg', self.black)[1]):
                                # do nothing from the second loop
                                continue
                            for i, image in enumerate(self.images):
                                self.processed_image_widgets[str(i)].value = bytes(
                                    cv2.imencode('.jpg', self.black)[1])
                                self.processed_image_widgets[str(i)].layout = {'width': str(
                                    80/len(self.images))+"%", 'height': '1px', 'border': '1px solid black'}

                        if self.stream_logs and self.streamlogs_widget.value:
                             self.streamlogs_text_widget.value = str(self.stream_logs)
                            

        def flag(change):
            if change['new'] == 'exit':
                self.camera.release()
                clear_output()
                # gc.collect()
                print("program ended properly")

            if change['new'] == 'disconnect':
                self.image_widget.value = bytes(
                    cv2.imencode('.jpg', self.image)[1])
                self.camera.release()
                self.logger.info('Camera Disconnected')

            if change['new'] == 'connect':
                if self.camera.isOpened() == False:
                    self.camera = cv2.VideoCapture(0)
                    self.camera.set(cv2.CAP_PROP_FOURCC,
                                    cv2.VideoWriter_fourcc(*"MJPG"))
                    self.camera.set(cv2.CAP_PROP_FPS, 30)

                # args = (self.state_widget, self.camera, self.image_widget,
                #        self.processed_image_widget, self.handler.out, self.acquire_image_widget)
                args = self.container
                execute_thread = threading.Thread(target=live, args=args)
                execute_thread.start()
                self.logger.info('Starting program')

            if change['new'] == 'pause':
                self.logger.info('Pausing program')
                pass

         # ipywidgets
        self.state_widget = ipywidgets.ToggleButtons(
            # options=['exit', 'disconnect', 'pause', 'connect'], description='', value='pause')
            options=['exit', 'disconnect', 'connect'], description='', value='disconnect')
        self.state_widget.observe(flag, names='value')
        self.fps_widget = ipywidgets.Text(
            value="fps: "+str(self.fps), placeholder='stream_logs area', layout={"width": "80%",'border': '1px solid black'})
        self.image_widget = ipywidgets.Image(format='jpeg', value=bytes(cv2.imencode(
            '.jpg', self.image)[1]), layout={"width": "80%", 'border': '1px solid black'})
        self.acquire_image_widget = ipywidgets.Button(
            description="acquire image", tooltip="acquire image")
        
        #basic
        self.container = [self.state_widget, #select stat
                     self.acquire_image_widget, #capture button
                     self.image_widget, #display input
                     self.fps_widget,  # fps
                     self.handler.out  # log
                     ]

        
        
        if self.pipeline_func:  # if pipeline func is present, insert a processed image widget and image analysis widget
            processed_image_widgets_list = []
            for key, w in self.processed_image_widgets.items():
                processed_image_widgets_list.append(w)
            
            self.processed_image_widget = ipywidgets.HBox(
                processed_image_widgets_list)
            
            self.container.insert(3, self.processed_image_widget)
            
            self.image_analysis_widget = ipywidgets.Checkbox(
                value=False, description="Enable Image Analysis Pipeline")
            self.hide_input_widget = ipywidgets.Checkbox(
                value=False, description="hide input image")
            
            checkboxes = [self.image_analysis_widget, self.hide_input_widget]
            if self.stream_logs is not None:
                self.streamlogs_widget = ipywidgets.Checkbox(
                value=False, description="display stream_logs")
                self.streamlogs_text_widget = ipywidgets.Text(layout={"width": "80%", 'border': '1px solid black'})
                
                self.container.insert(-1,self.streamlogs_text_widget) #stream logs    
                checkboxes.insert(1,self.streamlogs_widget)
            self.container.insert(2,ipywidgets.HBox(checkboxes,layout={"width": "80%"}))
                
        live_execution_widget = ipywidgets.VBox(self.container)
        display(live_execution_widget)