server {
    listen 8081;

    location / {
        include uwsgi_params;
        uwsgi_pass unix:/home/ubuntu/hnjobs/HackerNews-Jobs/app.sock;
    }
}