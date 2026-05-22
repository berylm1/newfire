FROM nginx:1.27-alpine

RUN rm -f /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/devhub.conf
COPY index.html /usr/share/nginx/html/index.html
