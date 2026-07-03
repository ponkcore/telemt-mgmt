// Dashboard — stats overview from GET /api/stats.
// AC2: shows active users, total connections, total traffic.
// AC10: includes @MTProxybot promotion card (link to t.me/MTProxybot).
// Per ARCH-001@0.1.1 §8: M6 attribution — @MTProxybot promotion card.

import { useEffect, useState } from "react";

import { api } from "../api/client";
import type { StatsResponse } from "../api/types";
import { StatsCard } from "../components/StatsCard";

function formatTraffic(bytes: number): string {
  if (bytes >= 1_073_741_824) return (bytes / 1_073_741_824).toFixed(2);
  if (bytes >= 1_048_576) return (bytes / 1_048_576).toFixed(2);
  if (bytes >= 1024) return (bytes / 1024).toFixed(2);
  return bytes.toString();
}

function trafficSuffix(bytes: number): string {
  if (bytes >= 1_073_741_824) return "ГБ";
  if (bytes >= 1_048_576) return "МБ";
  if (bytes >= 1024) return "КБ";
  return "Б";
}

export function Dashboard() {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchStats() {
      setLoading(true);
      setError(null);
      try {
        const data = await api.getStats();
        setStats(data);
      } catch (err) {
        setError("Ошибка загрузки статистики");
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchStats();
  }, []);

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Дашборд</h1>
        <p className="page-subtitle">Обзор статистики прокси-сервера</p>
      </div>

      {/* AC10 — @MTProxybot promotion card for M6 ad_tag attribution */}
      <div className="promo-card">
        <div className="promo-card-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--color-accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 11l18-5v12L3 14v-3z" />
            <path d="M11.6 16.8a3 3 0 1 1-5.8-1.6" />
          </svg>
        </div>
        <div className="promo-card-body">
          <div className="promo-card-title">@MTProxybot — Статистика продвижения</div>
          <div className="promo-card-desc">
            Проверьте статистику ad_tag: показы, подписки на канал
          </div>
        </div>
        <a
          href="https://t.me/MTProxybot"
          target="_blank"
          rel="noopener noreferrer"
          className="promo-card-link"
        >
          Открыть
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
            <polyline points="15 3 21 3 21 9" />
            <line x1="10" y1="14" x2="21" y2="3" />
          </svg>
        </a>
      </div>

      {error && <div className="form-error">{error}</div>}

      {loading ? (
        <div className="loading">
          <div className="spinner" />
          Загрузка статистики...
        </div>
      ) : stats ? (
        <>
          <div className="card-grid">
            <StatsCard label="Активные пользователи" value={stats.active_users} />
            <StatsCard label="Всего подключений" value={stats.total_connections} />
            <StatsCard
              label="Всего трафика"
              value={formatTraffic(stats.total_traffic)}
              suffix={trafficSuffix(stats.total_traffic)}
            />
          </div>

          <div className="grafana-card">
            <div className="grafana-card-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--color-warning)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 3v18h18" />
                <path d="M7 16l4-8 4 4 4-6" />
              </svg>
            </div>
            <div className="grafana-card-body">
              <div className="grafana-card-title">Grafana</div>
              <div className="grafana-card-desc">
                Детальная статистика и мониторинг прокси-сервера
              </div>
            </div>
            <a
              href="/grafana"
              target="_blank"
              rel="noopener noreferrer"
              className="grafana-card-link"
            >
              Открыть Grafana
            </a>
          </div>
        </>
      ) : null}
    </div>
  );
}
