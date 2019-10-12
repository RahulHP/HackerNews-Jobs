sudo cp backend.service /etc/systemd/system
sudo systemctl start backend
sudo systemctl enable backend
sudo cp backend /etc/nginx/sites-available/
sudo rm /etc/nginx/sites-enabled/backend
sudo ln -s /etc/nginx/sites-available/backend /etc/nginx/sites-enabled
sudo cp app.service /etc/systemd/system
sudo systemctl start app
sudo systemctl enable app
sudo cp app /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/app /etc/nginx/sites-enabled

sudo systemctl restart nginx