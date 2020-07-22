Usefull Commands



# Access jupyter over ssh port foward

**jetson nano side**

`jupyter lab`

To access the notebook, open this file in a browser:
        file:///home/phytometrics/.local/share/jupyter/runtime/nbserver-19269-open.html
    Or copy and paste one of these URLs:
        http://jetson-nano:8080/?token=xxxxxxxxx
     or http://127.0.0.1:8080/?token=xxxxxxxx

**client PC side**

`ssh -L 8080:localhost:8080 phytometrics@192.168.55.1` 

