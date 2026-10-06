"use client";

import { Suspense } from "react";
import { AuthFrame } from "../../components/AuthFrame";
import { GoogleAuth } from "../../components/GoogleAuth";

export default function SignInPage() {
  return (
    <AuthFrame>
      <Suspense fallback={<h1>Sign in</h1>}>
        <GoogleAuth title="Sign in" />
      </Suspense>
    </AuthFrame>
  );
}
