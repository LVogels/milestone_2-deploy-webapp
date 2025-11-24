FROM alpine:3.16

# Install lighttpd and curl for health checks
RUN apk add --no-cache lighttpd curl

# Copy custom lighttpd configuration
COPY lighttpd.conf /etc/lighttpd/lighttpd.conf

# Copy web content

COPY index.html /var/www/localhost/htdocs/

# Create a simple health check
RUN echo '#!/bin/sh' > /healthcheck.sh && \
    echo 'curl -f http://localhost/ || exit 1' >> /healthcheck.sh && \
    chmod +x /healthcheck.sh

# Expose port 80
EXPOSE 80

# Start lighttpd in foreground mode
CMD ["lighttpd", "-D", "-f", "/etc/lighttpd/lighttpd.conf"]

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD /healthcheck.sh