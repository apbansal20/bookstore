install required packages in the ubuntu instance. run pip3 -r install requirements.txt 
Also, make a directory named images in /tmp i.e. mkdir /tmp/images. 
the EC2 needs access to write to S3. So, attach an IAM role with S3 permissions. 
The DB parameters are present in db.properties. Make sure they are reachable.