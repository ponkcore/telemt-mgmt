// Users page — user table with search, pagination, disable/enable.
// AC3: lists users with pagination from GET /api/users.
// AC9: pagination design handles 1000+ users efficiently.

import { Layout } from "../components/Layout";
import { UserTable } from "../components/UserTable";

export function Users() {
  return (
    <Layout>
      <div className="page-header">
        <h1 className="page-title">Пользователи</h1>
        <p className="page-subtitle">Управление пользователями прокси</p>
      </div>
      <UserTable />
    </Layout>
  );
}
