# Server setup
Note that this guide assumes that you're logging in as user `ubuntu` and that you install the repo to `
/home/ubuntu/github/orchestration_server`. They also assume python 3.11. Change the instructions below if that's not correct.

## Install dependencies
```
sudo apt-get update
sudo apt-get upgrade
sudo apt-get install -y python3.11 python3.11-pip python3.11-dev python3.11-venv
```

## Clone and install this repo
```
cd /home/ubuntu/
mkdir github
cd github
git clone git@github.com:LivePublication/orchestration_server.git
```
Set up a virtual environment and install dependencies
```
cd orchestration_server
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## nginx setup
```
sudo apt-get install -y nginx
```
Copy the nginx config file to the nginx config directory
```
sudo cp /home/ubuntu/github/orchestration_server/setup/orchestration_server.nginx /etc/nginx/sites-available/orchestration_server
```
Edit the default server config:
```
sudo nano /etc/nginx/sites-available/default
```
Comment out the following lines:
```
root /var/www/html;
index index.html index.htm index.nginx-debian.html;
```

Replace the contents of
```
location / {
    # First attempt to serve request as file, then
    # as directory, then fall back to displaying a 404.
    try_files $uri $uri/ =404;
}
```
with:
```
location / {
    proxy_pass http://127.0.0.1:5000/;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-Prefix /;
}
```
being careful to keep the indentation correct.

Enable the new config:
```
sudo systemctl restart nginx
```
Check nginx is running:
```
sudo systemctl status nginx
```

## Set up a systemd service to serve the app via gunicorn
```
sudo cp /home/ubuntu/github/orchestration_server/setup/orchestration_server.service /etc/systemd/system/orchestration_server.service
sudo systemctl daemon-reload
sudo systemctl start orchestration_server
sudo systemctl enable orchestration_server
```

## Updating the code
```
cd /home/ubuntu/github/orchestration_server
git pull
sudo systemctl restart orchestration_server
```

# Testing the server
The server is running locally on port 5000, we haven't set up a reverse proxy yet (e.g.: nginx), as isn't meant to be exposed to the internet yet.

From you're local machine, you can forward port 5000 over ssh to send test requests to the server:
```
ssh -L 5000:localhost:5000 ubuntu@<server ip>
```

On the server, watch the gunicorn logs to see the requests come in:
```
watch -n 5 tail -n 50 ~/gunicorn.log
```

# Setting up SSL/HTTPS with LetsEncrypt/Certbot
## Create a DNS record
Set up openstack cli and run (worst-case need to setup everything):
```
mkdir openstack
cd openstack
sudo apt install -y python3.11 python3.11-dev python3.11-venv
sudo apt install -y gcc
python3.11 -m venv .venv
source .venv/bin/activate
pip install python-openstackclient python-designateclient
```
Get the credentials file from nectar and source it:
```
source LivePup-Globus-openrc.sh
```
Get the DNS zone ID (in this case, livepup-globus.cloud.edu.au.):
```
openstack zone list
```
Create the DNS record using that zone, the sub-domain name, and the host server ip:
```
openstack recordset create <zone-id> <name> --type A --record <server-ip>
```
## On the server, install certbot and run it
First ensure that the nginx config server name matches that of the DNS record you created above.
```
sudo nano /etc/nginx/sites-available/default
```
and add/edit the server_name line (without the trailing . or slash):
```
server_name <name>.<zone-id>;
```
check the config
```
sudo nginx -t
```

Finally, install certbot and run it:
```
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx
```

At this point, you should be able to access the server via https, and a systemd service (certbot.timer) should update the certificate before it renews.