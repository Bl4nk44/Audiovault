# Konfiguracja Reverse Proxy i SSL

Audiovault jest zaprojektowany z myślą o uruchamianiu go za systemem *Reverse Proxy* dla bezpieczeństwa i obsługi certyfikatów SSL/TLS. Wbudowana warstwa frontendowa w kontenerze Nginx samodzielnie dba o wewnętrzne rutowanie, należy jednak zapewnić odpowiednie skonfigurowanie nadrzędnego reverse proxy, aby:

1. Przekazywał żądania do portu frontendu (standardowo `2137`), a nie bezpośrednio do backendu na `8000`.
2. Dodawał odpowiednie nagłówki przekierowania (`X-Forwarded-For`, `X-Forwarded-Proto`, `Host`).
3. Pozwalał na nawiązywanie i utrzymanie połączeń WebSockets (`Upgrade`, `Connection: upgrade`).

Poniżej znajdują się instrukcje konfiguracyjne dla popularnych serwerów Reverse Proxy.

---

## 🟢 Nginx Proxy Manager (NPM)

Nginx Proxy Manager posiada bardzo proste GUI. Podczas konfiguracji "Proxy Host" w NPM upewnij się, że ustawienia są następujące:

1. Przejdź do **Proxy Hosts** -> **Add Proxy Host**:
   - **Domain Names**: Twoja wybrana domena (np. `audiovault.example.com`).
   - **Scheme**: `http`
   - **Forward Hostname / IP**: Wpisz IP maszyny serwera docker (lub nazwę kontenera `audiovault-frontend` jeśli NPM jest we wspólnej sieci docker).
   - **Forward Port**: `2137`
2. Zaznacz niezbędne opcje (Ważne!):
   - ✅ **Cache Assets** (Opcjonalnie, dla polepszenia wydajności)
   - ✅ **Block Common Exploits**
   - ✅ **Websockets Support** (Wymagane do działania postępu pobierania)
3. Przejdź do zakładki **SSL**:
   - Wybierz certyfikat (lub "Request a new SSL Certificate").
   - Zaznacz: **Force SSL** oraz **HTTP/2 Support**.

## 🔵 Traefik

Jeśli korzystasz z kontenera Traefik, użyj standardowych etykiet (docker labels). Musisz dodać ten kod do usługi `frontend` w `docker-compose.yml` dla Audiovault.

```yaml
services:
  frontend:
    # (reszta oryginalnej konfiguracji frontendu)
    labels:
      - "traefik.enable=true"
      # Router dla HTTP (oraz automatyczny redirect do HTTPS)
      - "traefik.http.routers.audiovault.rule=Host(`audiovault.example.com`)"
      - "traefik.http.routers.audiovault.entrypoints=websecure"
      - "traefik.http.routers.audiovault.tls.certresolver=letsencrypt" # lub Twój nazwany HTTP resolver
      
      # Wskazanie usługi wewnętrznej
      - "traefik.http.services.audiovault.loadbalancer.server.port=8080" # Nginx w kontenerze nasłuchuje na 8080 (mapowany na zewnątrz jako 2137)
```
*Uwaga: Wewnętrzny port frontendu Audiovault to z perspektywy dockera `8080`, zewnętrzny to `2137`. Traefik działający w wirtualnej współdzielonej podsieci winien wskazywać na natywny wewnątrz-kontenerowy port `8080`!*

## 🟡 Caddy

Caddy słynie z prostoty konfiguracyjnej - automatycznie zapięte są podstawowe proxy rules oraz przesyłanie socketów.
Dodaj blok do Twojego pliku `Caddyfile`:

```caddyfile
audiovault.example.com {
    reverse_proxy 127.0.0.1:2137
}
```

## 🟣 HAProxy

Wymagane jest jawne zdefiniowanie backendu przyjmującego gniazda websocketowe. Dodaj następującą konfigurację w pliku `/etc/haproxy/haproxy.cfg`:

```haproxy
frontend https-in
    bind *:443 ssl crt /ścieżka/do/certyfikatu.pem
    mode http
    
    # Przechwytywanie ruchu na domenę
    acl is_audiovault hdr(host) -i audiovault.example.com
    use_backend audiovault_backend if is_audiovault

backend audiovault_backend
    mode http
    
    # Zachowanie nagłówków Proxy i WebSocket
    option forwardfor
    http-request set-header X-Forwarded-Port %[dst_port]
    http-request add-header X-Forwarded-Proto https if { ssl_fc }
    
    server audiovault 127.0.0.1:2137 check
```

## 🟤 Zoraxy

Zoraxy, podobnie jak NPM oferuje GUI, ale z innym ułożeniem paneli:

1. Przejdź do sekcji **Proxy Rules** -> i dodaj w **Target**:
   - **Vdir / Virtual Directory Rule**
   - **Domain / Subdomain**: Wpisz `audiovault.example.com`.
   - **Target Host/IP**: Skopiuj `http://<TWE_LOKALNE_IP>:2137`.
2. Otwórz ustawienia dodanej ścieżki (Edit w Actions).
   - W sekcji **Websocket**: Zaznacz pozycję `Enable WebSocket Proxy`. (Bez tego, websockets w aplikacji będzie wpadać w TimeOut).
3. (Opcjonalnie) Przejdź pod **TLS/SSL**, upewnij się że przypięty jest certyfikat (SNI włącza samo Zoraxy automatycznie).

---

> **Pamiętaj**:  Gdy udostępniasz serwer przez Reverse Proxy, powinieneś w pliku `.env` Audiovault zaktualizować zmienną `ALLOWED_HOSTS` aby aplikacja ufała i nie odrzuciła ruchu ze względów bezpieczeństwa (np. `ALLOWED_HOSTS=audiovault.example.com,localhost`). Zaktualizuj także `BACKEND_CORS_ORIGINS=https://audiovault.example.com,http://localhost:2137`.
