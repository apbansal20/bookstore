#!/bin/bash
cd /home/ubuntu/app
nohup python3 application.py >> log.txt 
echo "hello world"