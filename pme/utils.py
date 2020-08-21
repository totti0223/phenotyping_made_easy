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
            'width': '80%',
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