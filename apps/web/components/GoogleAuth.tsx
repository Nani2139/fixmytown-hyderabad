"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { initializeApp, getApps } from "firebase/app";
import { getAuth, getRedirectResult, GoogleAuthProvider, signInWithPopup, signInWithRedirect } from "firebase/auth";
import { ApiError, api } from "../lib/api";

type FirebaseWebConfig = {
  apiKey: string;
  authDomain: string;
  projectId: string;
  appId: string;
};

export function GoogleAuth({ title }: { title: string }) {
  const router = useRouter();
  const next = useSearchParams().get("next") || "/";
  const [config, setConfig] = useState<FirebaseWebConfig | null>(null);
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    let cancel = false;
    api<{ google: boolean; firebase: FirebaseWebConfig | null }>("/v1/auth/config")
      .then(async (res) => {
        if (cancel) return;
        setConfig(res.firebase);
        setReady(true);
        if (!res.firebase) return;
        const auth = firebaseAuth(res.firebase);
        const cred = await getRedirectResult(auth);
        if (!cred || cancel) return;
        await finish(await cred.user.getIdToken());
      })
      .catch((e) => {
        if (!cancel) setErr(e instanceof ApiError ? e.message : "Could not load sign-in.");
        setReady(true);
      });
    return () => {
      cancel = true;
    };
    // finish is stable enough for the first load
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function finish(idToken: string) {
    await api("/v1/auth/google", { method: "POST", body: JSON.stringify({ id_token: idToken }) });
    router.push(next);
    router.refresh();
  }

  async function onGoogle() {
    if (!config) {
      setErr("Google sign-in needs the Firebase web app values in apps/api/.env.");
      return;
    }
    setBusy(true);
    setErr("");
    const auth = firebaseAuth(config);
    const provider = new GoogleAuthProvider();
    provider.setCustomParameters({ prompt: "select_account" });
    try {
      const cred = await signInWithPopup(auth, provider);
      await finish(await cred.user.getIdToken());
    } catch (e) {
      const code = e && typeof e === "object" && "code" in e ? String(e.code) : "";
      if (code === "auth/popup-blocked" || code === "auth/popup-closed-by-user") {
        if (code === "auth/popup-blocked") {
          await signInWithRedirect(auth, provider);
          return;
        }
        setErr("");
      } else if (e instanceof ApiError) {
        setErr(e.message);
      } else {
        setErr("Google sign-in did not finish.");
      }
      setBusy(false);
    }
  }

  return (
    <>
      <h1>{title}</h1>
      <p className="sub">Use the Google account you want on FixMyTown. The first sign-in creates your profile.</p>
      <button className="btn red wide" type="button" disabled={!ready || busy} onClick={onGoogle}>
        {busy ? "Opening Google…" : "Continue with Google"}
      </button>
      {err && <p className="form-error">{err}</p>}
      {!config && ready && (
        <p className="muted">
          Add FIREBASE_API_KEY, FIREBASE_AUTH_DOMAIN, FIREBASE_PROJECT_ID, and FIREBASE_APP_ID, then restart the API.
        </p>
      )}
    </>
  );
}

function firebaseAuth(config: FirebaseWebConfig) {
  const app = getApps()[0] ?? initializeApp(config);
  return getAuth(app);
}
