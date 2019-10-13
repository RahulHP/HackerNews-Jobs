sudo apt-get update
sudo apt-get install -y python3.6 python3-pip zip
sudo pip3 install --target /home/ubuntu/python requests==2.22.0 PyMySQL==0.9.3
zip -r /home/ubuntu/python.zip /home/ubuntu/python/