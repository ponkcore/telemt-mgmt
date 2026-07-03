// User table component with search, pagination, action buttons.
// Per ARCH-001@0.1.1 §3 C4: Users page (list, search, disable/enable, pagination).
// AC3: lists users with pagination from GET /api/users.
// AC9: designed for pagination to handle 1000+ users.

import { useCallback, useEffect, useState } from "react";

import { api } from "../api/client";
import type { UserListResponse } from "../api/types";

const PER_PAGE = 20;

export function UserTable() {
  const [data, setData] = useState<UserListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchUsers = useCallback(async (p: number) => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.getUsers(p, PER_PAGE);
      setData(result);
    } catch (err) {
      setError("Ошибка загрузки пользователей");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsers(page);
  }, [page, fetchUsers]);

  const filteredItems = data?.items.filter((u) =>
    search ? u.name.toLowerCase().includes(search.toLowerCase()) : true,
  ) ?? [];

  async function handleToggle(username: string, currentlyDisabled: boolean) {
    setActionLoading(username);
    try {
      if (currentlyDisabled) {
        await api.enableUser(username);
      } else {
        await api.disableUser(username);
      }
      await fetchUsers(page);
    } catch (err) {
      setError("Ошибка изменения статуса пользователя");
      console.error(err);
    } finally {
      setActionLoading(null);
    }
  }

  const totalPages = data ? Math.ceil(data.total / data.per_page) : 1;

  return (
    <div className="table-container">
      <div className="table-search">
        <input
          type="text"
          placeholder="Поиск по имени..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {error && <div className="form-error">{error}</div>}

      <div className="table-wrapper">
        {loading ? (
          <div className="loading">
            <div className="spinner" />
            Загрузка...
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="empty-state">Пользователи не найдены</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Имя</th>
                <th>Источник</th>
                <th>IP</th>
                <th>Подключения</th>
                <th>Статус</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.map((user) => (
                <tr key={user.name}>
                  <td style={{ fontFamily: "var(--font-mono)", fontSize: "var(--text-xs)" }}>
                    {user.name}
                  </td>
                  <td>{user.source}</td>
                  <td>{user.ip_count ?? "—"}</td>
                  <td>{user.connections ?? "—"}</td>
                  <td>
                    {user.is_disabled ? (
                      <span className="badge badge-danger">Отключён</span>
                    ) : (
                      <span className="badge badge-success">Активен</span>
                    )}
                  </td>
                  <td>
                    <button
                      className={`btn btn-sm ${user.is_disabled ? "btn-primary" : "btn-danger"}`}
                      onClick={() => handleToggle(user.name, user.is_disabled)}
                      disabled={actionLoading === user.name}
                    >
                      {actionLoading === user.name
                        ? "..."
                        : user.is_disabled
                          ? "Включить"
                          : "Отключить"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {data && (
        <div className="table-pagination">
          <span className="pagination-info">
            Страница {data.page} из {totalPages} · Всего: {data.total}
          </span>
          <div className="pagination-controls">
            <button
              className="btn btn-sm btn-primary"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1 || loading}
            >
              Назад
            </button>
            <button
              className="btn btn-sm btn-primary"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages || loading}
            >
              Вперёд
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
