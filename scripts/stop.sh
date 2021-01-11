#!/bin/bash
pid=`ps aux | grep python3 | grep -i application.py | cut -d " " -f 7`
kill -9 $pid