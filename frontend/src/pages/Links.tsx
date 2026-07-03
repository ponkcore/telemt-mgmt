// Links page — create labelled link, list with copy-to-clipboard, delete.
// AC4: creates labelled link via POST /api/links, displays tg://proxy with copy button.

import { useCallback, useEffect, useState } from "react";

import { api } from "../api/client";
import type { LinkResponse } from "../api/types";
import { Layout } from "../components/Layout";
import { LinkForm } from "../components/LinkForm";

export function Links() {
  const [links, setLinks] = useState<LinkResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const fetchLinks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getLinks();
      setLinks(data.items);
    } catch (err) {
      setError("Ошибка загрузки ссылок");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLinks();
  }, [fetchLinks]);

  function handleCreated(link: LinkResponse) {
    setLinks((prev) => [link, ...prev]);
    setToast("Ссылка создана");
    setTimeout(() => setToast(null), 3000);
  }

  async function handleDelete(id: number) {
    try {
      await api.deleteLink(id);
      setLinks((prev) => prev.filter((l) => l.id !== id));
      setToast("Ссылка удалена");
      setTimeout(() => setToast(null), 3000);
    } catch (err) {
      setError("Ошибка удаления ссылки");
      console.error(err);
    }
  }

  async function handleCopy(link: LinkResponse) {
    try {
      await navigator.clipboard.writeText(link.proxy_link);
      setCopiedId(link.id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  }

  return (
    <Layout>
      <div className="page-header">
        <h1 className="page-title">Ссылки</h1>
        <p className="page-subtitle">Создание и управление маркированными ссылками</p>
      </div>

      <LinkForm onCreated={handleCreated} />

      {error && <div className="form-error">{error}</div>}

      <div className="card" style={{ marginTop: "var(--space-6)" }}>
        <h3 style={{ fontSize: "var(--text-base)", marginBottom: "var(--space-4)" }}>
          Существующие ссылки
        </h3>

        {loading ? (
          <div className="loading">
            <div className="spinner" />
            Загрузка...
          </div>
        ) : links.length === 0 ? (
          <div className="empty-state">Нет созданных ссылок</div>
        ) : (
          <div>
            {links.map((link) => (
              <div key={link.id} className="link-item">
                <div className="link-item-info">
                  <div className="link-item-label">{link.label}</div>
                  <div className="link-item-url">{link.proxy_link}</div>
                </div>
                <div className="link-item-actions">
                  <button
                    className="btn btn-sm btn-primary"
                    onClick={() => handleCopy(link)}
                  >
                    {copiedId === link.id ? "Скопировано!" : "Копировать"}
                  </button>
                  <button
                    className="btn btn-sm btn-danger"
                    onClick={() => handleDelete(link.id)}
                  >
                    Удалить
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {toast && <div className="toast toast-success">{toast}</div>}
    </Layout>
  );
}
