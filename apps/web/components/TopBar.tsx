"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { api, type Me } from "../lib/api";
import { useI18n } from "../lib/i18n";

export function TopBar() {
  const { t, lang, setLang } = useI18n();
  const [me, setMe] = useState<Me["user"] | null>(null);
  const [open, setOpen] = useState(false);
  const path = usePathname();
  const router = useRouter();

  const links = [
    { href: "/", label: t("map") },
    { href: "/ask", label: t("ask") },
    { href: "/dashboard", label: t("tickets") },
  ];

  useEffect(() => {
    api<Me>("/v1/auth/me")
      .then((d) => setMe(d.user))
      .catch(() => setMe(null));
    setOpen(false);
  }, [path]);

  async function signOut() {
    await api("/v1/auth/signout", { method: "POST" });
    setMe(null);
    setOpen(false);
    router.push("/");
    router.refresh();
  }

  return (
    <header className="topbar">
      <Link href="/" className="brand">
        <img className="brand-logo" src="/brand/logo.png" alt="FixMyTown" />
      </Link>
      <nav className="desk">
        {links.map((l) => (
          <Link key={l.href} href={l.href} className={path === l.href ? "on" : ""}>
            {l.label}
          </Link>
        ))}
        {me?.role === "admin" ? (
          <Link href="/admin" className={path === "/admin" ? "on" : ""}>
            {t("admin")}
          </Link>
        ) : null}
        <Link href="/privacy" className={path === "/privacy" ? "on" : ""}>
          {t("legal")}
        </Link>
      </nav>
      <div className="top-actions">
        <div className="lang-split">
          <button type="button" className={lang === "en" ? "on" : ""} onClick={() => setLang("en")}>
            EN
          </button>
          <span>|</span>
          <button type="button" className={lang === "te" ? "on" : ""} onClick={() => setLang("te")}>
            తెలుగు
          </button>
        </div>
        <Link href={me ? "/account" : "/signin"} className="avatar" aria-label={t("account")}>
          {me?.email[0]?.toUpperCase() || ""}
        </Link>
        <button type="button" className="menu-btn" aria-label={t("menu")} onClick={() => setOpen((v) => !v)}>
          <span />
          <span />
        </button>
      </div>
      {open ? (
        <div className="account-menu">
          {me ? <p className="menu-email">{me.email}</p> : <Link href="/signin">{t("sign_in")}</Link>}
          {links.map((l) => (
            <Link key={l.href} href={l.href}>
              {l.label}
            </Link>
          ))}
          {me?.role === "admin" ? <Link href="/admin">{t("admin")}</Link> : null}
          <Link href="/privacy">{t("legal")}</Link>
          {me ? (
            <button type="button" onClick={signOut}>
              {t("sign_out")}
            </button>
          ) : null}
        </div>
      ) : null}
    </header>
  );
}
