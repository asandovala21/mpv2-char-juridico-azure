#!/bin/sh
envsubst '$BACKEND_URL' < /etc/nginx/conf.d/default.conf > /tmp/default.conf
mv /tmp/default.conf /etc/nginx/conf.d/default.conf
nginx -g 'daemon off;'
