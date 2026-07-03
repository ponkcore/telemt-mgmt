// React entry point — renders App into #root.
// Per ARCH-001@0.1.1 §3 C4: SPA entry point.

import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App";
import "./styles/global.css";

const rootElement = document.getElementById("root");
if (!rootElement) throw new Error("Root element #root not found");

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
