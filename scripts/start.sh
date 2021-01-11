#!/bin/bash
cd /home/ubuntu/app
nohup python3 application.py >> log.txt 2>/dev/null &
echo "hello world"