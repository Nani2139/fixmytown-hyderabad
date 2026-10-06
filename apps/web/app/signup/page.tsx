"use client";

import { Suspense } from "react";
import { AuthFrame } from "../../components/AuthFrame";
import { GoogleAuth } from "../../components/GoogleAuth";

export default function SignUpPage() {
  return (
    <AuthFrame>
      <Suspense fallback={<h1>Create an account</h1>}>
        <GoogleAuth title="Create an account" />
      </Suspense>
    </AuthFrame>
  );
}
