// Main layout with sidebar navigation and content area.
// Per ARCH-001@0.1.1 §3 C4: dark theme sidebar nav, card-based layout.

import type { ReactNode } from "react";

import { Sidebar } from "./Sidebar";

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-wrapper">
        <main className="app-content">{children}</main>
      </div>
    </div>
  );
}
