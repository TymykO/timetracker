FROM nginx:alpine

# Skopiuj custom konfigurację
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf

# Expose porty
EXPOSE 80 443

# CMD domyślny nginx
CMD ["nginx", "-g", "daemon off;"]
