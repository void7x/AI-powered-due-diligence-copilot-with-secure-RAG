"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Briefcase, Loader2 } from "lucide-react";
import { Button, Field, Input } from "@/components/ui";
import { useAuth } from "@/hooks/useAuth";

export default function LoginPage() {
  const { user, loading, login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("demo@example.com");
  const [password, setPassword] = useState("demo1234");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { if (!loading && user) router.replace("/dashboard"); }, [user, loading, router]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-navy-900 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center justify-center gap-2 text-white">
          <Briefcase size={22} />
          <span className="text-lg font-semibold tracking-tight">AI Due Diligence Copilot</span>
        </div>
        <form onSubmit={submit} className="card space-y-4 p-6" aria-label="Sign in">
          <h1 className="text-base font-semibold text-slate-900">Sign in to your workspace</h1>
          <Field label="Email">
            <Input type="email" autoComplete="email" required value={email}
                   onChange={(e) => setEmail(e.target.value)} placeholder="you@firm.com" />
          </Field>
          <Field label="Password">
            <Input type="password" autoComplete="current-password" required minLength={8}
                   value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
          </Field>
          {error && <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">{error}</p>}
          <Button type="submit" disabled={busy} className="w-full">
            {busy ? <Loader2 size={14} className="animate-spin" /> : null}
            {busy ? "Signing in…" : "Sign in"}
          </Button>
          <p className="text-center text-[11px] leading-relaxed text-slate-400">
            Demo account: <code className="rounded bg-slate-100 px-1">demo@example.com / demo1234</code>
            <br />(seeded automatically in development)
          </p>
        </form>
      </div>
    </main>
  );
}
