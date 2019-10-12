sudo cp nginx_setup/backend.service /etc/systemd/system
sudo systemctl start backend
sudo systemctl enable backend
sudo cp nginx_setup/backend /etc/nginx/sites-available/
sudo rm /etc/nginx/sites-enabled/backend
sudo ln -s /etc/nginx/sites-available/backend /etc/nginx/sites-enabled
sudo cp nginx_setup/app.service /etc/systemd/system
sudo systemctl start app
sudo systemctl enable app
sudo cp nginx_setup/app /etc/nginx/sites-available/
sudo rm /etc/nginx/sites-enabled/app
sudo ln -s /etc/nginx/sites-available/app /etc/nginx/sites-enabled

sudo systemctl restart nginx