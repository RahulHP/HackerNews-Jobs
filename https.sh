#!/usr/bin/env bash

sudo add-apt-repository -y ppa:certbot/certbot
sudo apt install -y python-certbot-nginx
sudo certbot --nginx -d test.rahulhp.me -n --agree-tos --email rahul.hphatak@gmail.com
