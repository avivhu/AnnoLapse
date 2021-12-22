#!/usr/bin/python3
import subprocess

service_name = 'annolapse.service'
subprocess.check_output(f'cp {service_name} /lib/systemd/system/{service_name}', shell=True)
subprocess.check_output(f'chmod 644 /lib/systemd/system/{service_name}', shell=True)
subprocess.check_output(f'systemctl start {service_name}', shell=True)
subprocess.check_output(f'sudo systemctl daemon-reload', shell=True)
subprocess.check_output(f'sudo systemctl enable {service_name}', shell=True)



