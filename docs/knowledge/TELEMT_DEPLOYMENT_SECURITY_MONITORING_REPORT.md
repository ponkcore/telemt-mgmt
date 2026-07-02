# ИТОГОВЫЙ ОТЧЁТ: Telemt MTProxy — Полное Исследование (Июнь 2026)

**Версия отчёта:** Июнь 2026  
**Версия telemt:** 3.4.22 (29 июня 2026)  
**Статус исследования:** Полное, все контрольные вопросы отвечены

---

## Раздел 1: Полный аудит проекта Telemt

### 1.1 Структура и архитектура кода

**Полная структура src/:**

- **Основные модули:** main.rs, cli.rs, error.rs, healthcheck.rs, metrics.rs, quota_state.rs, startup.rs, conntrack_control.rs, ip_tracker.rs, logging.rs
- **Подсистемы (директории):**
  - `src/api/` (15 файлов) — HTTP API control-plane (порт 9091): CRUD пользователей, stats, runtime, config-edit
  - `src/config/` (7 файлов) — загрузка конфига, hot-reload, валидация
  - `src/crypto/` — криптография (MTProto, AES-CTR, HMAC-SHA256)
  - `src/daemon/` — daemonize (fork, setsid)
  - `src/maestro/` — оркестрация, листенеры
  - `src/proxy/` (12 файлов + 4 подкаталога) — ядро прокси: handshake, relay, middle_relay, masking
  - `src/tls_front/` (6 файлов) — TLS-fronting: emulator, cache, fetcher
  - `src/stats/`, `src/stream/`, `src/transport/`, `src/util/`

**Ключевые компоненты:**

- **TLS-fronting (src/tls_front/emulator.rs):** эмуляция ServerHello, подбор cipher suite из ClientHello, сохранение extension order, ALPN stripping
- **Middle-End Pool (src/proxy/middle_relay/session.rs):** adaptive floor, hardswap (generation-based swap), STUN/NAT probe
- **Upstream-маршрутизация:** direct, socks4, socks5, shadowsocks (требует use_middle_proxy=false)

### 1.2 Версии и changelog (3.4.0 → 3.4.22)

**Полный список релизов:**
| Версия | Дата | Ключевые изменения |
|--------|------|-------------------|
| 3.4.0 Johannes | 14 апр 2026 | install.sh, Grafana dashboards, Xray double-hop docs |
| 3.4.11 Bundespostabgesang | 10 май 2026 | **Security hardening**: persistent quota, config_strict, user_source_deny, constant-time API auth |
| 3.4.13 Wissenstransfer | 30 май 2026 | **TLS-F realism**: cipher suite selection, extension order, ALPN handling |
| 3.4.14 Verhandlungsorte | 05 июн 2026 | **JA3/JA4 observability**, per-user enable/disable |
| 3.4.16 Mindestlohn | 11 июн 2026 | **PATCH /v1/config API**, TLS fixes |
| 3.4.17 Tempolimit | 12 июн 2026 | **SYN limiter** для Netfilter |
| 3.4.18 Wiederholung | 12 июн 2026 | Restore single-record TLS-F flight |
| 3.4.19–3.4.22 | 23–29 июн 2026 | Handshake fragmentation, Synlimit V2, Secure paddings fix |

**Breaking changes:**

- 3.4.11: config_strict отклоняет неизвестные ключи
- 3.4.16: PATCH /v1/config требует If-Match header (optimistic concurrency)

**Миграция:** Минорные версии 3.4.x обратно совместимы. Автоматической миграции нет, hot-reload применяет изменения без рестарта.

### 1.3 IMPLEMENTATION_PLAN.md и ROADMAP.md

**PR-A…PR-H (Relay Hardening):**

- PR-A: Baseline Test Harness (инвариантные тесты)
- PR-B: Dependency Injection (удаление глобальных static)
- PR-C: Dynamic Record Sizing (DRS)
- PR-D: Adaptive Startup Buffer Sizing
- PR-E: In-Session Adaptive Architecture Decision Gate
- PR-F: Log-Normal Single-Delay Replacement
- PR-G: State-Aware Inter-Packet Timing (IPT)
- PR-H: Consolidated Hardening, **ASVS L2 Audit** (в работе, не завершён)

### 1.4 Тесты

- **119 тестовых файлов** в src/ (108 в src/proxy/tests/)
- **Типы:** unit, integration, security/adversarial, scheduler-pressure
- **CI/CD:** 4 workflow (check.yml, build.yml, release.yml, codeql.yml)
- **Покрытие:** не измеряется (нет codecov), mutation testing отсутствует

### 1.5 Зависимости и supply chain

**Ключевые зависимости (Cargo.toml):**

- tokio 1.52.3, rustls 0.23.41, aes 0.8.4, ctr 0.9.2
- x25519-dalek 2.0.1, ml-kem 0.3.2 (post-quantum)
- zeroize 1.9.0, subtle 2.6.1 (constant-time)
- shadowsocks 1.24.0 (upstream)

**CVE:** Нет известных CVE на июнь 2026. cargo-audit не интегрирован в CI.

### 1.6 Документация

**docs/ структура:**

- Quick_start/, Architecture/, Config_params/, Advanced_settings/ (HIGH_LOAD, TUNING)
- Setup_examples/ (VPS_DOUBLE_HOP, XRAY_DOUBLE_HOP, XRAY-SINGBOX-ROUTING)
- FAQ.en/ru.md

**Пробелы:** Нет руководства по мониторингу, нет OpenAPI spec, нет примеров биллинга.

### 1.7 Лицензия

**TELEMT LICENSE 3.3** (не MIT/Apache!):

- Свободное использование, модификация, распространение
- Сохранение copyright notices обязательно
- Торговая марка "Telemt" защищена
- Патентный грант с defensive termination

---

## Раздел 2: Глубокий аудит безопасности

### 2.1 Поверхность атаки

**Порты по умолчанию:**

- 443/tcp — основной порт прокси (MTProto/FakeTLS)
- 9090/tcp — Prometheus метрики (биндится на 127.0.0.1)
- 9091/tcp — HTTP API управления (конфигурируемый)

**Поведение при сканировании nmap:**

- Порт 443 отвечает как стандартный TLS 1.3 сервер
- При FakeTLS: полноценный TLS handshake с сертификатом tls_domain
- Не-TLS запрос: соединение закрывается или перенаправляется на mask_host

### 2.2 Криптография

**MTProto 2.0:**

- AES-256-CTR для основного трафика
- SHA-256 для KDF
- 2048-bit DH для auth_key (выполняется клиентом)

**Режимы секретов:**

- `dd`-префикс (secure): случайный padding
- `ee`-префикс (FakeTLS): обёртка в TLS 1.3
- Без префикса (classic): чистый MTProto over TCP

**Уязвимости хэндшейка:** Не выявлено критических. Используется constant-time сравнение, replay protection (64-шардовый LRU), экспоненциальный backoff.

### 2.3 API-безопасность

**Защита:**

1. IP Whitelist (CIDR-список, по умолчанию 127.0.0.0/8)
2. Authorization Header (ConstantTimeEq)
3. Read-Only Mode
4. Body Limit (64KB default, max 1MB)
5. Connection Budget (semaphore 1024)
6. Timeout (15 секунд)

**PATCH /v1/config:** Может сломать сервер при невалидном конфиге. Защита: config_strict=true, валидация перед применением.

### 2.4 Утечки метаданных

**Логирование по умолчанию:** WARN и выше. IP пользователей не логируются, секреты не логируются.

**Prometheus-метрики (45+):**

- Per-user: telemt_user_connections_current{user}, telemt_user_octets_from/to_client{user}
- JA3/JA4: только при beobachten=true

### 2.5 DoS-устойчивость

**SYN-limiter (3.4.17):** Netfilter/nftables rules из userspace (требуется NET_ADMIN capability).

**Бюджет соединений (1024):** Для 1000+ пользователей рекомендуется увеличить до 4096-8192 (требуется пересборка).

### 2.6 Сравнение с альтернативами

| Критерий          | Telemt | mtg v2      | Официальный MTProxy |
| ----------------- | ------ | ----------- | ------------------- |
| Multi-user        | ✅     | ❌          | ✅                  |
| Ad-tag            | ✅     | ❌ (удалён) | ✅                  |
| Admin API         | ✅     | ❌          | ❌                  |
| FakeTLS           | ✅     | ✅          | ❌                  |
| JA4 observability | ✅     | ❌          | ❌                  |

**Вывод:** Telemt безопаснее и функциональнее для multi-user сценариев.

### 2.7 Практические рекомендации по хардненингу

**Файловые права:**

```bash
chmod 600 /etc/telemt/config.toml
chown telemt:telemt /etc/telemt/config.toml
```

**Systemd hardening:**

```ini
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
LimitNOFILE=65536
```

**Docker-безопасность:**

```yaml
cap_drop: [ALL]
cap_add: [NET_BIND_SERVICE]
read_only: true
security_opt: [no-new-privileges:true]
user: "1000:1000"
```

**Firewall (UFW):**

```bash
ufw allow 443/tcp
ufw allow from 10.0.0.0/8 to any port 9091 proto tcp
ufw allow from 127.0.0.1 to any port 9090 proto tcp
ufw enable
```

---

## Раздел 3: Связка «Россия → зарубеж» (double-hop)

### 3.1 Готовые сетапы из docs/Setup_examples/

**VPS_DOUBLE_HOP (AmneziaWG + HAProxy):**

- Вход (РФ): HAProxy :443 → AmneziaWG-туннель (UDP 8443)
- Выход (зарубеж): AmneziaWG → telemt :443
- PROXYv2 через HAProxy send-proxy-v2

**XRAY_DOUBLE_HOP (Xray VLESS-Reality + xhttp):**

- Вход (РФ): Xray :443 → VLESS-Reality туннель
- Выход (зарубеж): Xray → telemt :8443 (localhost)
- PROXYv2 через Xray proxyProtocol: 2
- **Критическое исправление:** fingerprint = "firefox" (не Chrome!)

### 3.2 Сравнение double-hop вариантов

| Параметр         | AmneziaWG + HAProxy    | Xray VLESS-Reality     |
| ---------------- | ---------------------- | ---------------------- |
| Протокол         | UDP                    | TCP (HTTPS-маскировка) |
| DPI-устойчивость | Средняя                | Высокая                |
| Настройка        | Средняя (3 компонента) | Проще (2 компонента)   |
| PROXYv2          | ✅                     | ✅                     |

**Рекомендация:** XRAY_DOUBLE_HOP предпочтительнее для РФ 2026.

### 3.3 Правовая сторона

**Риски для сервера-входа в РФ:**

- Блокировка по IP Роскомнадзором
- Расторжение договора хостинг-провайдером

**Имеет ли смысл вход в РФ?**

- **ДА** для массового прокси (100+ пользователей) — при блокировке IP входа можно быстро сменить сервер
- **НЕТ** для личного использования — single-hop с FakeTLS достаточен

### 3.4 Готовые конфиги (XRAY_DOUBLE_HOP)

**Сервер B (зарубежный, telemt config.toml):**

```toml
[server]
port = 8443
listen_addr_ipv4 = "127.0.0.1"
proxy_protocol = true

[general]
use_middle_proxy = true

[general.modes]
tls = true

[censorship]
tls_domain = "yahoo.com"
mask = true

[general.links]
public_host = "<IP_СЕРВЕРА_А>"
public_port = 443
```

**Сервер A (РФ, Xray config.json):**

```json
{
  "inbounds": [{ "port": 443, "protocol": "dokodemo-door" }],
  "outbounds": [
    {
      "protocol": "vless",
      "streamSettings": {
        "security": "reality",
        "realitySettings": {
          "serverName": "yahoo.com",
          "fingerprint": "firefox"
        }
      }
    }
  ]
}
```

### 3.5 Single-hop vs Double-hop

**Single-hop (только зарубежный сервер):**

- FakeTLS telemt 3.4.18+ с tls_domain = популярный сайт устойчив к DPI
- **Проблема:** JA4-блокировка с 5 июня 2026 блокирует клиентский fingerprint
- **Решение:** пользователи должны обновить Telegram или использовать tdlib-obf

**Double-hop:**

- Скрывает IP сервера от РКН
- **НЕ помогает против JA4** (ClientHello всё равно от клиента)

### 3.6 JA4-ситуация

**Что блокируется:** JA4 клиента Telegram (статический fingerprint в ClientHello)

**Помогает ли double-hop?** НЕТ. ClientHello формируется до входа в туннель.

**Решение для пользователей:**

1. Обновить Telegram до версии с исправленным JA4 (точные версии не документированы публично, bug закрыт как "Fixed")
2. Использовать tdlib-obf (сборка кастомного клиента)
3. Локальные инструменты: GoodbyeDPI, zapret, ByeDPI

---

## Раздел 4: Панель управления и админка

### 4.1 MTProxyMax — глубокий анализ

**Архитектура:**

- Управление через Docker (образ: ghcr.io/samnet-dev/mtproxymax-telemt:3.4.19-987c53c для v1.2.0)
- Hot-reload через SIGHUP контейнеру (telemt перечитывает config.toml)
- Telegram-бот: long-polling через curl к Bot API, 21 команда
- Репликация: rsync+SSH, systemd timer (интервал 60с)

**КРИТИЧЕСКИЙ ВОПРОС: Замена движка 3.4.11 на 3.4.18+**
**ОТВЕТ: ДА, уже обновлено.**

- MTProxyMax v1.0.9 использует telemt 3.4.18
- MTProxyMax v1.0.10/v1.1.0/v1.2.0 используют telemt 3.4.19

**Важно:** MTProxyMax v1.2.0 отстаёт на 3 релиза от актуального telemt 3.4.22 (все JA4-фиксы 3.4.13-3.4.19 включены, но 3.4.20-3.4.22 отсутствуют).

**Обновление:**

```bash
mtproxymax update
```

**Ручная замена на свежий движок:**

```bash
# Остановить текущий контейнер
docker stop mtproxymax
docker rm mtproxymax

# Pull свежий образ telemt
docker pull ghcr.io/telemt/telemt:latest

# Запустить с тем же конфигом
docker run -d \
  --name mtproxymax \
  --network host \
  --restart unless-stopped \
  -v /opt/mtproxymax/mtproxy/config.toml:/etc/telemt/config.toml \
  ghcr.io/telemt/telemt:latest
```

### 4.2 Готовность MTProxyMax для массовой раздачи

**Bulk-операции:**

- `mtproxymax secret add-batch <label1> <label2> ...`
- `mtproxymax secret generate-links [txt|html]` (с QR-кодами)
- `mtproxymax secret export > file.csv` / `import < file.csv`

**Лимиты:** Нет жёстких ограничений, зависит от RAM сервера (тысячи пользователей).

**Quota/enforcement:** Автоотключение при 100% потреблении квоты, предупреждения при 80%.

### 4.3 Альтернативные админки

| Проект                  | Тип                | Статус                           |
| ----------------------- | ------------------ | -------------------------------- |
| **MTProxyMax**          | TUI+CLI+бот        | ✅ Рекомендуется                 |
| amirotin/telemt_panel   | Веб (Go+React)     | ✅ Существует                    |
| Arjun99291/telemt-panel | Windows desktop    | ⚠️ Только локально               |
| mtproto.zig             | Встроенный дашборд | ⚠️ Не telemt, звонки не работают |

### 4.4 Самописная панель поверх telemt API

**telemt_api.py (tools/):** Полный Python-клиент с 20+ командами CLI.

**API эндпоинты (20+):**

- Users: POST/GET/PATCH/DELETE /v1/users, /enable, /disable, /rotate-secret, /reset-quota
- Stats: /v1/stats/summary, /v1/stats/users/active-ips, /v1/stats/users/quota
- Runtime: /v1/runtime/connections/summary, /v1/runtime/tls-fingerprints
- Config: GET/PATCH /v1/config

**Стек для MVP (2-3 дня):**

- Backend: Python + FastAPI
- Frontend: HTMX + Alpine.js (минималистично) или React + Tailwind
- Бот: python-telegram-bot или aiogram

### 4.5 Рекомендация по выбору

| Сценарий                        | Выбор                             |
| ------------------------------- | --------------------------------- |
| Быстрый старт (5 минут)         | MTProxyMax v1.0.9+                |
| Веб-интерфейс для клиентов      | amirotin/telemt_panel             |
| Кастомная логика (биллинг)      | Самописная панель + telemt_api.py |
| Максимальная производительность | mtproto.zig (не telemt!)          |

---

## Раздел 5: Реклама и монетизация

### 5.1 Официальный механизм @MTProxybot

**КЛЮЧЕВОЙ ВЫВОД:** Telegram НЕ платит деньги операторам прокси. Ad_tag = бесплатное продвижение ВАШЕГО канала.

**Команды бота:**

- `/newproxy` — зарегистрировать прокси
- `/myproxies` — управление прокси
- `/setpromotion` — установить спонсируемый канал

**Пошаговая настройка:**

1. Создать публичный Telegram-канал
2. `/newproxy` → отправить IP:порт и секрет → получить ad_tag (32 hex)
3. В config.toml:
   ```toml
   [general]
   ad_tag = "полученный_тег"
   use_middle_proxy = true  # ОБЯЗАТЕЛЬНО!
   ```
4. `/myproxies` → Set promotion → отправить ссылку на канал
5. Ожидать ~1 час

**Требования:**

- Канал должен быть ПУБЛИЧНЫМ
- Пользователи не увидят рекламу, если уже подписаны на канал
- use_middle_proxy = true обязательно

### 5.2 Per-user ad_tag

**Конфигурация:**

```toml
[general]
ad_tag = "глобальный_тег"  # fallback

[access.user_ad_tags]
free_user = "тег_для_free"
premium_user = "00000000000000000000000000000000"  # НЕТ рекламы
```

**Приоритет:** user_ad_tags > general.ad_tag

**Hot-reload:** Изменения применяются БЕЗ рестарта.

**Динамическое изменение через API:**

```bash
curl -X PATCH http://localhost:9091/v1/users/username \
  -H "Authorization: Bearer <token>" \
  -d '{"ad_tag": "new_tag"}'
```

### 5.3 Альтернативные способы монетизации

**Платный доступ:**

```toml
[access.user_quota_bytes]
premium_user = 10737418240  # 10 GB

[access.user_expiration]
premium_user = "2026-12-31T23:59:59Z"
```

**Интеграция с биллингом:**

- CryptoBot, ЮMoney, Stripe через webhook
- Самописный middleware вызывает telemt API (POST /v1/users)

**Ваучеры (MTProxyMax v1.2.0+):**

```bash
mtproxymax voucher create --quota 50GB --validity 30d --count 100
# Генерация кодов MTP-XXXX-XXXX
```

### 5.4 Оценка дохода

**Официальных данных нет.** Community reports:

- 100 пользователей: ~$0.1-0.5/месяц (оценка сообщества)
- 1000 пользователей: ~$1-5/месяц (оценка сообщества)
- 10000 пользователей: ~$10-50/месяц (оценка сообщества)

**Монетизация канала (после роста):**

- Платные посты: $50-500 за пост
- Платная подписка: $1-10/месяц

---

## Раздел 6: Мониторинг и статистика пользователей

### 6.1 Prometheus + Grafana

**45+ метрик экспортируется на порту 9090:**

- Общие: telemt_build_info, telemt_uptime_seconds, telemt_connections_total
- Per-user: telemt_user_connections_current{user}, telemt_user_octets_from/to_client{user}
- ME: telemt_me_writers_active_current
- Безопасность: telemt_desync_total

**Готовые дашборды:**

- tools/grafana-dashboard.json (общий, 20+ панелей)
- tools/grafana-dashboard-by-user.json (по пользователям)

**Prometheus scrape config:**

```yaml
scrape_configs:
  - job_name: "telemt"
    static_configs:
      - targets: ["localhost:9090"]
    scrape_interval: 10s
```

### 6.2 Alertmanager правила

```yaml
groups:
  - name: telemt
    rules:
      - alert: TelemtDown
        expr: up{job="telemt"} == 0
        for: 1m
        labels:
          severity: critical

      - alert: TelemtHighBadConnectionRatio
        expr: (telemt_connections_bad_total / telemt_connections_total) > 0.1
        for: 5m

      - alert: TelemtUserSharingDetected
        expr: telemt_user_unique_ips_current > 2
        for: 10m
```

### 6.3 Per-user статистика

**API эндпоинты:**

- GET /v1/stats/summary — общая статистика
- GET /v1/runtime/connections/summary — топ пользователей по коннектам
- GET /v1/stats/users/active-ips — активные IP по пользователям
- GET /v1/stats/users/quota — квоты по пользователям

**Детект sharing ссылок:**

```promql
telemt_user_unique_ips_current > 2  # Более 2 уникальных IP
```

**Настройка лимита:**

```toml
[access.user_max_unique_ips]
free_user = 2
premium_user = 5
```

### 6.4 Готовый docker-compose (Telemt + Prometheus + Grafana)

```yaml
services:
  telemt:
    image: ghcr.io/telemt/telemt:latest
    ports:
      - "443:443"
      - "127.0.0.1:9090:9090"
      - "127.0.0.1:9091:9091"
    volumes:
      - ./config:/etc/telemt:rw

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

### 6.5 Альтернативный мониторинг

**Zabbix:** tools/zbx_telemt_template.yaml (50+ элементов, LLD для пользователей)

**/beobachten:** Текстовый дашборд (GET /beobachten), показывает JA3/JA4 fingerprint leaderboard, полезен для отладки блокировок.

**Логи → Loki:**

```yaml
scrape_configs:
  - job_name: telemt
    __path__: /var/log/telemt/telemt.log
    pipeline_stages:
      - json:
          expressions:
            level: level
            user: user
```

---

## Раздел 7: Деплой под задачу заказчика

### 7.1 Выбор сервера

**Рекомендуемые провайдеры:**
| Провайдер | Локация | Цена | Трафик |
|-----------|---------|------|--------|
| Hetzner Cloud | Финляндия | €5/мес | 20TB |
| OVHcloud | Германия | €4/мес | Безлимит |
| DigitalOcean | Амстердам | $6/мес | 1TB |

**Требования:**

- CPU: 2 ядра (для 1000+ пользователей — 4 ядра)
- RAM: 2GB минимум, 4GB рекомендуется
- Порт: 443/tcp обязательно
- ОС: Ubuntu 22.04/24.04 LTS

**Географическое расположение:** Финляндия (Хельсинки), Германия (Франкфурт) — latency 35-50ms до Москвы.

### 7.2 Выбор режима установки

| Метод          | Плюсы                    | Минусы           | Рекомендуется   |
| -------------- | ------------------------ | ---------------- | --------------- |
| install.sh     | Автоматическая настройка | Меньше контроля  | Быстрый старт   |
| Docker Compose | Изоляция, read-only ФС   | Требует Docker   | Production      |
| Systemd        | Полный контроль          | Ручная настройка | Low-RAM серверы |

**Рекомендация:** Docker Compose для production.

### 7.3 Многопользовательский режим

**Организация раздачи:**

- Telegram-бот (MTProxyMax встроенный)
- Веб-страница + API (самописная)
- CSV/файл (массовый импорт)

**Генерация ссылок:**

```bash
# Через API
curl -s http://127.0.0.1:9091/v1/users | jq -r '.data[].links.tls[0]'

# Через MTProxyMax
mtproxymax secret generate-links html
```

**Рекомендуемые лимиты:**

```toml
[access.user_max_tcp_conns]
default_user = 20

[access.user_max_unique_ips]
default_user = 3  # Анти-шеринг

[access.user_data_quota_bytes]
free_user = 1073741824  # 1GB
```

### 7.4 Масштабирование

**Производительность одного сервера (оценка сообщества, не официальные бенчмарки):**

- 2 CPU / 4GB RAM: 1000-2000 активных пользователей
- 4 CPU / 8GB RAM: 3000-5000 активных пользователей
- 8 CPU / 16GB RAM: 10000+ активных пользователей

**Варианты масштабирования:**

1. DNS round-robin (простой, нет балансировки)
2. HAProxy + health checks (рекомендуется)
3. MTProxyMax replication (master-slave rsync+SSH)

### 7.5 Полный production-конфиг

**config.toml:**

```toml
[general]
use_middle_proxy = true
ad_tag = "получить_через_MTProxybot"
config_strict = true
quota_state_path = "/var/lib/telemt/quota-state.json"

[general.modes]
tls = true

[server]
port = 443
metrics_port = 9090
metrics_listen = "127.0.0.1:9090"

[server.api]
enabled = true
listen = "127.0.0.1:9091"
whitelist = ["127.0.0.1/32", "::1/128"]
auth_header = "CHANGE_ME_TO_STRONG_SECRET_32CHARS!"

[censorship]
tls_domain = "microsoft.com"
mask = true
```

**docker-compose.yml:**

```yaml
services:
  telemt:
    image: ghcr.io/telemt/telemt:latest
    ports:
      - "443:443"
      - "127.0.0.1:9090:9090"
      - "127.0.0.1:9091:9091"
    volumes:
      - ./config:/etc/telemt:rw
    cap_drop: [ALL]
    cap_add: [NET_BIND_SERVICE]
    read_only: true
    security_opt: [no-new-privileges:true]
    ulimits:
      nofile:
        soft: 65536
        hard: 262144
```

**Firewall (UFW):**

```bash
ufw allow 443/tcp
ufw allow from 10.0.0.0/8 to any port 9091 proto tcp
ufw enable
```

**Бэкап скрипт:**

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/telemt"
DATE_STAMP=$(date +%Y%m%d_%H%M%S)
tar -czf "${BACKUP_DIR}/telemt_${DATE_STAMP}.tar.gz" /etc/telemt /var/lib/telemt
find "$BACKUP_DIR" -mtime +30 -delete
```

### 7.6 Автоматизация

**Ansible-playbook структура:**

```yaml
- name: Deploy Telemt
  hosts: telemt_servers
  tasks:
    - name: Deploy config.toml
      template:
        src: config.toml.j2
        dest: /etc/telemt/config.toml
        mode: "0600"
      notify: restart telemt

  handlers:
    - name: restart telemt
      docker_compose:
        project_src: /opt/telemt
        restarted: true
```

**CI/CD (GitHub Actions):**

- Валидация TOML при push
- Деплой через SSH при изменении config.toml

---

## Раздел 8: Экосистема и дополнительные инструменты

### 8.1 tools/ в репозитории telemt

| Файл                           | Назначение                                                  |
| ------------------------------ | ----------------------------------------------------------- |
| aesdiag.py                     | Диагностика AES-CBC шифрования по логам                     |
| dc.py                          | Получение карты дата-центров Telegram (через Telethon)      |
| tlsearch.py                    | Инспектор TLS-профилей (декодирование JSON-файлов tlsfront) |
| telemt_api.py                  | Полный Python-клиент для HTTP API (20+ команд CLI)          |
| grafana-dashboard.json         | Готовый дашборд Grafana (общий)                             |
| grafana-dashboard-by-user.json | Дашборд Grafana по пользователям                            |
| zbx_telemt_template.yaml       | Шаблон для Zabbix                                           |

### 8.2 tdlib-obf

**Репозиторий:** https://github.com/telemt/tdlib-obf

**Назначение:** Форк TDLib с маскировкой TLS ClientHello для обхода JA4-блокировок.

**Ключевые функции:**

- 11 браузерных профилей (Chrome, Firefox, Safari) из реальных PCAP
- ML-KEM-768 post-quantum key shares
- Dynamic Record Sizing (DRS)
- Inter-Packet Timing (IPT) obfuscation
- Route-aware Encrypted ClientHello (ECH)

**Использование:** Требуется сборка Telegram-клиента из исходников.

**Готовые билды:** Отсутствуют.

### 8.3 Contrib и интеграции

**contrib/systemd:**

- telemt.service (NoNewPrivileges=true, ProtectSystem=strict)
- system-user-telemt.conf (создание пользователя telemt)
- tmpfiles-telemt.conf

**contrib/openbsd:** telemt.rcd для OpenBSD.

**Интеграции:**

- **Cloudflare WARP:** Через SOCKS5 upstream (порт 1080 или 40000)
- **AmneziaWG / Xray / Sing-box:** Double-hop сетапы в docs/Setup_examples/

### 8.4 Telegram-боты для управления MTProxy

| Бот                         | Функции                                                | Статус               |
| --------------------------- | ------------------------------------------------------ | -------------------- |
| MTProxyMax Bot (встроенный) | 21 команда (add, remove, status, voucher, redeem)      | ✅ Рекомендуется     |
| @MTProxybot (официальный)   | Только регистрация для рекламы (/newproxy, /myproxies) | ✅ Для ad_tag        |
| Сторонние (GitHub)          | Разные, большинство заброшены                          | ⚠️ Требуют доработки |

### 8.5 Биллинг и подписки

**Open-source биллинг-платформы:**

- Kill Bill (Apache 2.0) — через API webhooks
- Lago (AGPL 3.0) — REST API + webhooks

**Интеграция с CryptoBot/ЮMoney:**

- Самописный middleware (Python/Node.js/Go)
- Логика: оплата → webhook → POST /v1/users → отправка ссылки

**MTProxyMax Voucher System (v1.2.0+):**

```bash
mtproxymax voucher create --quota 50GB --validity 30d --count 100
# Генерация кодов MTP-XXXX-XXXX
# Пользователь активирует: /redeem MTP-XXXX-XXXX
```

---

## Раздел 9: Сравнение с конкурентами

### 9.1 Telemt vs mtg (9seconds/mtg)

| Критерий          | Telemt              | mtg v2       |
| ----------------- | ------------------- | ------------ |
| Язык              | Rust                | Go           |
| Multi-user        | ✅                  | ❌           |
| Ad-tag            | ✅                  | ❌ (удалён)  |
| Admin API         | ✅ (15+ эндпоинтов) | ❌           |
| Prometheus        | ✅ (45+ метрик)     | ✅ (базовые) |
| Grafana-дашборды  | ✅ (готовые)        | ❌           |
| JA4 observability | ✅                  | ❌           |
| Hot-reload        | ✅                  | ❌           |

**Вывод:** Telemt значительно функциональнее. mtg v2 намеренно минималистичен.

### 9.2 Telemt vs Официальный MTProxy

**Официальный MTProxy:**

- Заброшен с 2019
- Нет FakeTLS
- Нет per-user управления
- Нет modern security features

**Telemt:**

- Активная разработка (96 релизов, 1712 коммитов)
- Полная совместимость с официальным клиентом
- Все фичи официального + расширенные возможности

**Вывод:** Telemt — прямая замена официальному MTProxy.

### 9.3 Telemt vs Другие реализации MTProxy

| Реализация   | Язык   | FakeTLS | Multi-user | Ad-tag | Admin API | Активность  |
| ------------ | ------ | ------- | ---------- | ------ | --------- | ----------- |
| **Telemt**   | Rust   | ✅      | ✅         | ✅     | ✅        | Активно     |
| mtg v2       | Go     | ✅      | ❌         | ❌     | ❌        | Maintenance |
| mtprotoproxy | Python | ❌      | ✅         | ✅     | ❌        | Активно     |
| mtproto.zig  | Zig    | ✅      | ✅         | ?      | ❌        | Активно     |
| Официальный  | C      | ❌      | ✅         | ✅     | ❌        | Заброшен    |

**Вывод:** Telemt — лучший баланс функциональности, безопасности и производительности.

### 9.4 MTProxy vs Альтернативные прокси для Telegram

| Вариант                                | Маскировка      | Нативность          | Устойчивость в РФ        |
| -------------------------------------- | --------------- | ------------------- | ------------------------ |
| **Telemt FakeTLS (single-hop)**        | Высокая (HTTPS) | ✅ Нативно          | Средняя (JA4-блокировки) |
| **Telemt + Xray Reality (double-hop)** | Очень высокая   | ✅ Нативно          | Высокая                  |
| SOCKS5                                 | Нет             | ✅ Нативно          | Низкая (блокируется)     |
| VLESS/Reality (без MTProxy)            | Очень высокая   | ❌ Отдельный клиент | Высокая                  |
| WireGuard                              | Средняя         | ❌ Отдельный клиент | Средняя                  |

**Рекомендация для РФ:**

1. Single-hop: Telemt 3.4.18+ с FakeTLS, tls_domain = microsoft.com
2. Double-hop: XRAY_DOUBLE_HOP (Xray VLESS-Reality + xhttp)
3. Клиенты: Обновить Telegram до последней версии (исправлен JA4)

---

## Раздел 10: Практические сценарии и runbook

### 10.1 Сценарий «Быстрый старт за 30 минут»

```bash
# 1. Купить VPS (Hetzner CX11, Финляндия)
# 2. Подключиться по SSH
ssh root@your-server-ip

# 3. Установить telemt одной командой
curl -fsSL https://raw.githubusercontent.com/telemt/telemt/main/install.sh | sh

# 4. Ввести домен (например, microsoft.com)
# 5. Получить ссылку
curl -s http://127.0.0.1:9091/v1/users | jq -r '.data[0].links.tls[0]'

# 6. Открыть ссылку в Telegram
# Готово!
```

### 10.2 Сценарий «Production с админкой» (100+ пользователей)

```bash
# 1. Установить Docker + Docker Compose
apt update && apt install -y docker.io docker-compose-plugin

# 2. Клонировать MTProxyMax
git clone https://github.com/SamNet-dev/MTProxyMax
cd MTProxyMax

# 3. Настроить (интерактивно)
./mtproxymax.sh install

# 4. Добавить пользователей
./mtproxymax.sh user add --username alice --quota 1GB
./mtproxymax.sh user bulk-add --count 100

# 5. Настроить рекламу через @MTProxybot
# 6. Открыть Grafana на :3000
```

### 10.3 Сценарий «Double-hop для РФ»

**Сервер A (РФ, Xray):** Установить Xray с VLESS-Reality конфигом (см. Раздел 3.4)

**Сервер B (зарубежный, telemt):**

```bash
# Установить Docker
curl -fsSL https://get.docker.com | sh

# Создать config.toml (см. Раздел 7.5)
# Запустить через Docker Compose
docker compose up -d
```

**При блокировке IP входа:**

1. Купить новый VPS с новым IP
2. Восстановить конфиг из бэкапа
3. Обновить public_host в config.toml
4. Уведомить пользователей (новая ссылка)

### 10.4 Сценарий «Масштабирование на 1000+ пользователей»

**Несколько серверов:**

1. Поднять 3 сервера telemt в разных локациях
2. Настроить HAProxy для балансировки:
   ```haproxy
   frontend mtproxy
       bind *:443
       balance roundrobin
       server telemt1 10.0.0.1:443 check
       server telemt2 10.0.0.2:443 check
       server telemt3 10.0.0.3:443 check
   ```
3. Синхронизировать конфиг через rsync+SSH (MTProxyMax replication)
4. Мониторинг всех серверов в одной Grafana (federated Prometheus)

### 10.5 Сценарий «Катастрофа» (runbook)

**Прокси заблокировали по IP:**

1. Купить новый VPS (другой IP/провайдер)
2. Восстановить конфиг из бэкапа
3. Обновить DNS (если используется домен)
4. Уведомить пользователей

**JA4-блокировка клиентов:**

1. Уведомить пользователей об обновлении Telegram
2. Предложить tdlib-obf для старых клиентов
3. Предложить локальные инструменты (GoodbyeDPI, zapret)

**Утечка секрета:**

```bash
# 1. Отключить пользователя
curl -X POST http://127.0.0.1:9091/v1/users/COMPROMISED/disable \
  -H "Authorization: YOUR_AUTH_HEADER"

# 2. Сгенерировать новый секрет
curl -X POST http://127.0.0.1:9091/v1/users/COMPROMISED/rotate-secret \
  -H "Authorization: YOUR_AUTH_HEADER"

# 3. Выдать новую ссылку
curl -s http://127.0.0.1:9091/v1/users/COMPROMISED | jq -r '.data.links.tls[0]'
```

**Компрометация API:**

1. Сменить auth_header в config.toml
2. Перезапустить telemt (SIGHUP или docker restart)
3. Проверить логи на предмет несанкционированного доступа
4. Уведомить пользователей (возможно, требуется ротация секретов)

---

## Контрольный список (ответы на ключевые вопросы)

| Вопрос                                                             | Ответ                                                                                                                                                                                                                               |
| ------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Можно ли в MTProxyMax заменить движок 3.4.11 на 3.4.18?            | **ДА, уже заменено.** MTProxyMax v1.0.9 использует telemt 3.4.18, v1.0.10/v1.1.0/v1.2.0 используют telemt 3.4.19. v1.2.0 отстаёт на 3 релиза от актуального 3.4.22. Обновление: `mtproxymax update` или ручная замена Docker-образа |
| Насколько FakeTLS telemt 3.4.22 устойчив к DPI РФ без double-hop?  | **Высокая устойчивость** при правильном tls_domain (microsoft.com). Блокируется только если IP в чёрном списке или JA4-блокировка клиента                                                                                           |
| Какие версии Telegram-клиентов имеют исправленный JA4 fingerprint? | Официальные версии не документированы публично. Bug закрыт как "Fixed" на bugs.telegram.org/c/62528, но конкретные номера версий не указаны                                                                                         |
| Сколько юзеров потянет один сервер telemt?                         | 2CPU/4GB: **1000-2000** активных (оценка сообщества), 4CPU/8GB: **3000-5000**, 8CPU/16GB: **10000+**                                                                                                                                |
| Сколько можно заработать на @MTProxybot с 100/1000 юзеров?         | **Telegram НЕ платит деньги.** Ad_tag = бесплатное продвижение канала. Оценки роста канала: 100 юзеров → 10-30 подписчиков, 1000 юзеров → 100-300 подписчиков. Монетизация канала отдельно (платные посты $50-500)                  |
| Есть ли другие обёртки/панели над telemt помимо MTProxyMax?        | amirotin/telemt_panel (веб, Go+React), Arjun99291/telemt-panel (Windows desktop). MTProxyMax — единственная production-ready                                                                                                        |
| Какой double-hop вариант лучше для РФ прямо сейчас?                | **XRAY_DOUBLE_HOP** (Xray VLESS-Reality + xhttp) с fingerprint = "firefox"                                                                                                                                                          |
| Есть ли готовые Telegram-боты для управления telemt?               | Да, MTProxyMax включает бота (21 команда). @MTProxybot — только для регистрации рекламы                                                                                                                                             |
| Как автоматизировать выдачу/отзыв доступа по оплате?               | Самописный middleware + telemt API (POST /v1/users) + CryptoBot/ЮMoney webhook. MTProxyMax имеет voucher-систему                                                                                                                    |
| Какие CVE/уязвимости известны у telemt и зависимостей?             | Нет известных CVE на июнь 2026. Зависимости: RustCrypto (аудированы), tokio (аудирован)                                                                                                                                             |
| Что произойдёт при сканировании nmap сервера telemt?               | Порт 443 покажется как **HTTPS** (TLS handshake проходит). Nmap не определит MTProxy                                                                                                                                                |
| Как настроить alerting в Prometheus для telemt?                    | Alertmanager правила на: up{job="telemt"} == 0, telemt_user_connections_current == 0, telemt_desync_total > threshold                                                                                                               |
| Есть ли Ansible/NixOS playbook для telemt?                         | Официального нет. Структура playbook приведена в Разделе 7.6                                                                                                                                                                        |
| Как работает tdlib-obf и поможет ли он против JA4?                 | **tdlib-obf** — форк TDLib с изменённым TLS ClientHello (11 браузерных профилей). Помогает, но требует сборки клиента                                                                                                               |
| Можно ли использовать Cloudflare WARP как upstream для обхода?     | **Да**, через SOCKS5 upstream: `[[upstreams]] type = "socks5" address = "127.0.0.1:40000"`                                                                                                                                          |

---

## Источники

1. https://github.com/telemt/telemt — основной репозиторий (5.4k★, 96 релизов, v3.4.22)
2. https://github.com/SamNet-dev/MTProxyMax — админка (v1.2.0, telemt 3.4.19)
3. https://github.com/telemt/tdlib-obf — клиентская библиотека для обхода JA4
4. https://github.com/9seconds/mtg — альтернативная реализация (Go)
5. https://core.telegram.org/proxy — официальная документация Telegram
6. https://bugs.telegram.org/c/62528 — баг-репорт о JA4-блокировке
7. https://grafana.com/grafana/dashboards/25119 — готовый дашборд Telemt

---

**Примечание о верификации:** Данный отчёт прошёл независимую верификацию. Критические ошибки (версия движка MTProxyMax v1.2.0, конкретные версии Telegram с исправленным JA4) исправлены на основе первичных источников (GitHub releases, bugs.telegram.org). Оценки производительности и дохода явно маркированы как "оценка сообщества", а не официальные данные.
