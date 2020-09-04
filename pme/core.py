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


class stream:
    def __init__(self, pipeline_func=None, output_directory=None, camera_id=None, camera_sets=None, sanity_check_image=None):

        self.image = np.zeros(shape=(100, 200, 3),
                              dtype=np.uint8)  # initial image. will be overrided by the sanity image and finally camera input.
        self.pipeline_func = pipeline_func
        self.camera_id = camera_id
        self.pipeline_func = pipeline_func
        self.camera_sets = camera_sets
        self.black = np.zeros((1, 1, 3), dtype=np.uint8)

        if output_directory == None:
            self.path = os.path.join(os.getcwd(), "data")
        else:
            self.path = output_directory

        if not os.path.exists(self.path):
            os.makedirs(self.path)
        print("- images will be saved to %s" % self.path)
        self.processed_image_widgets = {}

        if self.pipeline_func:
            if sanity_check_image:
                self.image = sanity_check_image
                assert_image_format(self.image)
            self.ret = wrapper(self.pipeline_func, self.image)

            if self.ret["csv_logs"] is not None:
                csv_name = datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv"
                self.csv_path = os.path.join(self.path,csv_name)
                print("- csv_logs will be written to %s" % self.csv_path)
                with open(self.csv_path, "a") as f:
                    if self.ret["csv_header"] is not None:
                        self.ret["csv_header"].insert(0,"file_name")
                        writer = csv.writer(f, lineterminator='\n')
                        writer.writerow(self.ret["csv_header"])

            self.layout = {'width': str(
                95/len(self.ret["images"]))+"%", 'height': '1px', 'border': '1px solid black'}
            for i in range(len(self.ret["images"])):
                self.processed_image_widgets[str(i)] = ipywidgets.Image(
                    format='jpeg', value=bytes(cv2.imencode('.jpg', self.image)[1]), layout=self.layout)

        assert self.camera_id is not None, "must specify a camera number for camera streaming"

        # assert video device is closed. must use a global variable for now
        # cv2.VideoCapture(self.camera_id).release()        
        self.camera = cv2.VideoCapture(self.camera_id)
        assert self.camera.isOpened(
        ), "problem with establishing connection with camera. check connection or camera_id"

        if self.camera_sets is not None:
            self.camera_sets(self.camera) 
        success,frame = self.camera.read()
        assert success == True, "error reading image from camera. check camera settings e.g. resolution, fps, format"
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
        
        self.launch()
        
    def launch(self):
        def capture(_):
            
            
            base = datetime.now().strftime("%Y%m%d_%H%M%S")
            basefile = base + ".jpg"
            orig_file = os.path.join(self.path, basefile)
            cv2.imwrite(orig_file, self.image)
            self.logger.info("input image saved as %s." % base)

            if self.ret["images"] is not None and self.image_analysis_widget.value == True:
                for i, image in enumerate(self.ret["images"]):
                    _base = base + "__"+str(i)+".jpg"
                    processed_file = os.path.join(
                        self.path, _base)
                    cv2.imwrite(os.path.join(self.path, processed_file), image)
                    self.logger.info(
                        "processed image saved as %s" % _base)

                if self.ret["csv_logs"] is not None and len(self.ret["csv_logs"]) !=0:                
                    with open(self.csv_path, "a") as f:
                        writer = csv.writer(f, lineterminator='\n')
                        for line in self.ret["csv_logs"]:
                            s = ([base, *line])
                            writer.writerow(s)
                    self.logger.info("csv logged")

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
                            'width': "95%", 'border': '1px solid black'}
                        self.image_widget.value = bytes(cv2.imencode(
                            '.jpg', self.image)[1])  # original input
                    else:
                        self.image_widget.layout = {
                            'width': "95%", 'height': '1px', 'border': '1px solid black'}
                        self.image_widget.value = bytes(cv2.imencode(
                            '.jpg', self.black)[1])  # original input

                    if self.pipeline_func is not None:
                        # apply pipeline and visualize processed images only when the analysis checkbox is ticked
                        if self.image_analysis_widget.value:
                            #self.images, self.csv_logs, self.stream_logs = wrapper(
                            #    self.pipeline_func, self.image)
                            self.ret = wrapper(self.pipeline_func, self.image)
                            
                            for i, image in enumerate(self.ret["images"]):
                                self.processed_image_widgets[str(i)].value = bytes(
                                    cv2.imencode('.jpg', image)[1])
                                self.processed_image_widgets[str(i)].layout = {'width': str(
                                    95/len(self.ret["images"]))+"%", 'border': '1px solid black'}
                                
                        else:  # if checkbox is unticked, force the height of the layout to 1px and hide
                            if self.processed_image_widgets["0"].value != bytes(cv2.imencode('.jpg', self.black)[1]):
                                # do nothing from the second loop
                                continue
                            for i, image in enumerate(self.ret["images"]):
                                self.processed_image_widgets[str(i)].value = bytes(
                                    cv2.imencode('.jpg', self.black)[1])
                                self.processed_image_widgets[str(i)].layout = {'width': str(
                                    95/len(self.ret["images"]))+"%", 'height': '1px', 'border': '1px solid black'}

                        if self.ret["stream_logs"] and self.streamlogs_widget.value:
                             self.streamlogs_text_widget.value = str(self.ret["stream_logs"])
                            

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
                    self.camera = cv2.VideoCapture(self.camera_id)
                    if self.camera_sets is not None:
                        self.camera_sets(self.camera)
                args = self.container
                execute_thread = threading.Thread(target=live, args=args)
                execute_thread.start()
                self.logger.info('Starting program')

            if change['new'] == 'pause':
                self.logger.info('Pausing program')
                pass

         # ipywidgets
        self.state_widget = ipywidgets.ToggleButtons(
            options=['exit', 'disconnect', 'pause', 'connect'], description='', value='pause')
            #options=['exit', 'disconnect', 'connect'], description='', value='disconnect')
        self.state_widget.observe(flag, names='value')
        self.fps_widget = ipywidgets.Text(
            value="fps: "+str(self.fps), placeholder='stream_logs area', layout={"width": "95%",'border': '1px solid black'})
        self.image_widget = ipywidgets.Image(format='jpeg', value=bytes(cv2.imencode(
            '.jpg', self.image)[1]), layout={"width": "95%", 'border': '1px solid black'})
        self.acquire_image_widget = ipywidgets.Button(
            description="acquire image", tooltip="acquire image")
        self.hide_input_widget = ipywidgets.Checkbox(
            value=False, description="Hide Input")
        #basic
        self.container = [self.state_widget, #select stat
                     self.acquire_image_widget, #capture button
                     self.hide_input_widget,
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
            
            self.container.insert(4, self.processed_image_widget)
            
            self.image_analysis_widget = ipywidgets.Checkbox(
                value=False, description="Enable Image Analysis Pipeline")
            self.hide_input_widget = ipywidgets.Checkbox(
                value=False, description="Hide Input")
            del self.container[2] #delete hide_input_widget
            checkboxes = [self.image_analysis_widget, self.hide_input_widget]
            
            if self.ret["stream_logs"] is not None:
                self.streamlogs_widget = ipywidgets.Checkbox(
                value=False, description="Display Stream Logs")
                self.streamlogs_text_widget = ipywidgets.Text(layout={"width": "95%", 'border': '1px solid black'})
                
                self.container.insert(-1,self.streamlogs_text_widget) #stream logs    
                checkboxes.insert(1,self.streamlogs_widget)
            self.container.insert(2,ipywidgets.HBox(checkboxes,layout={"width": "95%"}))
                
        live_execution_widget = ipywidgets.VBox(self.container)
        display(live_execution_widget)