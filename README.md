# AnnoLapse

Create a year-long timelapse video.


## Setup

### Azure Storage
* The images are uploaded to an Azure Storage blob container.

1. Create an Azure Storage account. 
    * Select the lowest priced storage type.
1. Edit or create a `.env` file with this content.
    ```
    TIMELAPSE_AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;<...>"
    ```

### Logging and Health Monitoring with Azure
1. Create an Azure Application Insights resource.
1. Edit or create a `.env` file with this content.
    ```
    APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=<...>"
    ```



### Systemd service
The `annolapse` service starts up the timelapse recorded automatically when your Raspberry Pi powers up.

To install:
```
sudo chmod 644 *.service
cp *.service /etc/systemd/system/
sudo systemctl enable annolapse.service
sudo systemctl enable annolapse_watchdog.service
```

## Troubleshooting

### Print the system log:
```
    tail -f  /var/log/syslog
```
### Run manually and debug

1. Stop service, then run the program
```
systemctl stop annolapse.service
python3 timelapse.py
```
    
    
