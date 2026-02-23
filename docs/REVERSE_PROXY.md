# Reverse Proxy & SSL Configuration

Audiovault is designed to run behind a **Reverse Proxy** for security and SSL/TLS certificate handling. The built-in frontend layer inside the Nginx container handles internal routing on its own, but you still need to configure your upstream reverse proxy to:

1. Forward requests to the frontend port (default `2137`), not directly to the backend at `8000`.
2. Pass the appropriate forwarding headers (`X-Forwarded-For`, `X-Forwarded-Proto`, `Host`).
3. Allow WebSocket connections to be established and maintained (`Upgrade`, `Connection: upgrade`).

Below you will find configuration instructions for the most popular reverse proxy servers.

---

## 🟢 Nginx Proxy Manager (NPM)

Nginx Proxy Manager has a very simple GUI. When configuring a **Proxy Host** in NPM, make sure the settings are as follows:

1. Go to **Proxy Hosts** → **Add Proxy Host**:
   - **Domain Names**: Your chosen domain (e.g. `audiovault.example.com`).
   - **Scheme**: `http`
   - **Forward Hostname / IP**: Enter the IP of your Docker host machine (or the container name `audiovault-frontend` if NPM shares the same Docker network).
   - **Forward Port**: `2137`
2. Enable the required options (Important!):
   - ✅ **Cache Assets** (Optional, for improved performance)
   - ✅ **Block Common Exploits**
   - ✅ **Websockets Support** (Required for download-progress functionality)
3. Go to the **SSL** tab:
   - Select a certificate (or choose **Request a new SSL Certificate**).
   - Enable: **Force SSL** and **HTTP/2 Support**.

## 🔵 Traefik

If you are using a Traefik container, use standard Docker labels. Add the following to the `frontend` service in Audiovault's `docker-compose.yml`.

```yaml
services:
  frontend:
    # (rest of the original frontend configuration)
    labels:
      - "traefik.enable=true"
      # Router for HTTP (with automatic redirect to HTTPS)
      - "traefik.http.routers.audiovault.rule=Host(`audiovault.example.com`)"
      - "traefik.http.routers.audiovault.entrypoints=websecure"
      - "traefik.http.routers.audiovault.tls.certresolver=letsencrypt" # or your named HTTP resolver

      # Internal service port
      - "traefik.http.services.audiovault.loadbalancer.server.port=8080" # Nginx inside the container listens on 8080 (mapped externally as 2137)
```
*Note: Audiovault's internal frontend port from Docker's perspective is `8080`; the external port is `2137`. Traefik operating on the shared virtual Docker network should point to the native in-container port `8080`!*

## 🟡 Caddy

Caddy is known for its configuration simplicity — basic proxy rules and WebSocket forwarding are handled automatically.
Add the following block to your `Caddyfile`:

```caddyfile
audiovault.example.com {
    reverse_proxy 127.0.0.1:2137
}
```

## 🟣 HAProxy

You need to explicitly define a backend that handles WebSocket connections. Add the following to your `/etc/haproxy/haproxy.cfg`:

```haproxy
frontend https-in
    bind *:443 ssl crt /path/to/certificate.pem
    mode http

    # Capture traffic for the domain
    acl is_audiovault hdr(host) -i audiovault.example.com
    use_backend audiovault_backend if is_audiovault

backend audiovault_backend
    mode http

    # Preserve proxy and WebSocket headers
    option forwardfor
    http-request set-header X-Forwarded-Port %[dst_port]
    http-request add-header X-Forwarded-Proto https if { ssl_fc }

    server audiovault 127.0.0.1:2137 check
```

## 🟤 Zoraxy

Zoraxy, like NPM, offers a GUI but with a different panel layout:

1. Go to the **Proxy Rules** section and add a new entry under **Target**:
   - **Vdir / Virtual Directory Rule**
   - **Domain / Subdomain**: Enter `audiovault.example.com`.
   - **Target Host/IP**: Paste `http://<YOUR_LOCAL_IP>:2137`.
2. Open the settings for the newly added rule (Edit in Actions).
   - Under **Websocket**: Check `Enable WebSocket Proxy`. (Without this, WebSockets in the application will time out.)
3. (Optional) Go to **TLS/SSL** and make sure a certificate is attached (Zoraxy enables SNI automatically).

---

> **Remember**: When exposing your server through a reverse proxy, you should update the `ALLOWED_HOSTS` variable in Audiovault's `.env` file so the application trusts incoming traffic and does not reject it for security reasons (e.g. `ALLOWED_HOSTS=audiovault.example.com,localhost`). Also update `BACKEND_CORS_ORIGINS=https://audiovault.example.com,http://localhost:2137`.
