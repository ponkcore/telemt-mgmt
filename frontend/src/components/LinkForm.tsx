// Form for creating a labelled link (label input → POST /api/links).
// Per ARCH-001@0.1.1 §3 C4: Links page (create labelled link form).
// AC4: creates labelled link via POST /api/links.

import { useState } from "react";

import { api } from "../api/client";
import type { LinkResponse } from "../api/types";

interface LinkFormProps {
  onCreated: (link: LinkResponse) => void;
}

export function LinkForm({ onCreated }: LinkFormProps) {
  const [label, setLabel] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!label.trim()) {
      setError("Введите название ссылки");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const link = await api.createLink({ label: label.trim() });
      onCreated(link);
      setLabel("");
    } catch (err) {
      setError("Ошибка создания ссылки");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <form onSubmit={handleSubmit}>
        {error && <div className="form-error">{error}</div>}
        <div className="form-group">
          <label className="form-label" htmlFor="link-label">
            Название ссылки
          </label>
          <input
            id="link-label"
            type="text"
            placeholder="например, forum-4pda"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            maxLength={128}
            disabled={loading}
          />
        </div>
        <div className="form-actions">
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? "Создание..." : "Создать ссылку"}
          </button>
        </div>
      </form>
    </div>
  );
}
