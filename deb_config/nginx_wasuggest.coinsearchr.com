server {
    server_name wasuggest.coinsearchr.com;

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/main/WolframAlphaSuggest/wasuggest.sock;
    }

    access_log /var/log/nginx/wasuggest.access.log;

    client_max_body_size 100M;
    charset utf-8;

    #listen 127.0.0.1:8080; # for Tor Hidden Service

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/coinsearchr.com-0001/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/coinsearchr.com-0001/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot




}

# Created for HTTPS Dev
#server {
#    server_name coinsearchr.com www.coinsearchr.com;

#    location / {
#        include proxy_params;
#        proxy_pass http://localhost:5000;
#    }

#    listen 5001 ssl; # managed by Certbot
#    ssl_certificate /etc/letsencrypt/live/coinsearchr.com/fullchain.pem; # managed by Certbot
#    ssl_certificate_key /etc/letsencrypt/live/coinsearchr.com/privkey.pem; # managed by Certbot
#    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
#    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot#
#}

server {
    if ($host = wasuggest.coinsearchr.com) {
        return 301 https://$host$request_uri;
    } # managed by Certbot

    server_name wasuggest.coinsearchr.com;

    listen 80;

    return 404; # managed by Certbot
}

