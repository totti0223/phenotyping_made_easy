import subprocess
import re
import logging

import ipywidgets
from IPython.display import display

class OutputWidgetHandler(logging.Handler):
    """
    Custom logging handler sending logs to an output widget
    https://ipywidgets.readthedocs.io/en/latest/examples/Output%20Widget.html#Integrating-output-widgets-with-the-logging-module:
    """

    def __init__(self, *args, height='100px', **kwargs):
        super(OutputWidgetHandler, self).__init__(*args, **kwargs)
        layout = {
            'width': '95%',
            'height': height,
            'border': '1px solid black'
        }
        #self.out = ipywidgets.Output(layout=layout)
        self.out = ipywidgets.Textarea(layout=layout)
        #self.out = ipywidgets.Output()

    def emit(self, record):
        """ Overload of logging.Handler method """
        formatted_record = self.format(record) + "\n"
        self.out.value = formatted_record + self.out.value
        self.out.value[:1000000]
        # memory limit. limit to 1Mb for now.

    def show_logs(self):
        """ Show the logs """
        display(self.out)

    def clear_logs(self):
        """ Clear the current logs """
        self.out.clear_output()

def wrapper(func, image):
    '''
    wrapper function of a custom pipeline. using a wrapper for flexibility in the future.
    '''
    ret = func(image)
    assert type(
        ret) == dict, "returned value of a custom pipeline must be a dictionary format"

    if "images" not in ret:
        #print("images not in return value. will prepare a pseudo data")
        ret["images"] = [np.zeros(shape=(50, 200, 3), dtype=np.uint8)]
    else:
        if type(ret["images"]) != list:
            ret["images"] = [ret["images"]]
                             
    if "csv_logs" not in ret:
        ret["csv_logs"] = None
    else:
        if type(ret["csv_logs"]) != list:
            ret["csv_logs"] = [ret["csv_logs"]]
    if "csv_header" not in ret:
        ret["csv_header"] = None    
    if "stream_logs" not in ret:
        ret["stream_logs"] = None

    return ret

def scan_camera_settings(camera_id, camera_backend=None):
    def _v4l2(camera_id):
        # this command is for linux only
        cmd = 'v4l2-ctl --device /dev/video' + \
            str(camera_id) + ' --list-formats-ext'
        proc = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
        outs_bytes = proc.communicate()[0]
        outs_str = outs_bytes.decode('utf-8')
        assert "Failed" not in outs_str, "failed to fetch information. check connection or camera id."
        outs_str_lists = outs_str.split('\n')
        d = {}
        i = 0
        for line in outs_str_lists:
            if "Pixel Format" in line:
                pixelformat = line.split(":")[-1].strip()
                if "MJPG" in pixelformat:
                    pixelformat = ['M', 'J', 'P', 'G']
                elif "YUYV" in pixelformat:
                    pixelformat = ['Y', 'U', 'Y', 'V']                
            if "Size:" in line:
                resolution = line.split()[-1]
            if "Interval" in line:
                fps = re.findall("(?<=\().+?(?=\))", line)[0].split()[0]
                _d = {"format": pixelformat, "height": int(resolution.split(
                    "x")[1]), "width": int(resolution.split("x")[0]), "fps": int(float(fps))}
                d[i] = _d
                i += 1
        return d
    d = _v4l2(camera_id)
    camera_list = []
    for k, v in d.items():
        camera_list.append(v)
    return camera_list