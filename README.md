# AnnoLapse

Create a year-long timelapse video.


## Setup

### Azure storage
The images are uploaded to an Azure Storage blob.

1. Create an Azure Storage blob. Select the lowest priced storage type.


1. Copy the blob connection string from Azure Portal.

1. Create .env file with this content:
```
TIMELAPSE_AZURE_STORAGE_CONNECTION_STRING=<CONNECTION_STRING>
```


### Systemd service
The `annolapse` service starts up the timelapse recorded automatically when your raspberry pi powers up.

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
    
    
