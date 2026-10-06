"use client";

import type { ReactNode } from "react";

export function AuthFrame({ children }: { children: ReactNode }) {
  return (
    <main className="auth-split hide-chrome">
      <section className="auth-hero">
        <img
          src="/brand/signin-hero.jpg"
          alt="Charminar with the FixMyTown pin and street-issue icons."
        />
      </section>
      <section className="auth-panel">{children}</section>
    </main>
  );
}
