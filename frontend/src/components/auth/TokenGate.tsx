"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getToken, setToken } from "@/lib/auth/token";

interface TokenGateProps {
  children: React.ReactNode;
}

export function TokenGate({ children }: TokenGateProps) {
  const [hasToken, setHasToken] = useState<boolean | null>(null);
  const [value, setValue] = useState("");

  useEffect(() => {
    const sync = () => setHasToken(Boolean(getToken()));
    sync();
    window.addEventListener("algoreel:token-changed", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("algoreel:token-changed", sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  if (hasToken === null) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="font-mono text-xs text-muted-foreground">authenticating…</div>
      </div>
    );
  }

  if (hasToken) return <>{children}</>;

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed) return;
    setToken(trimmed);
    setValue("");
  };

  return (
    <Dialog open={true}>
      <DialogContent hideClose className="max-w-md">
        <div className="space-y-1">
          <DialogTitle>Authenticate</DialogTitle>
          <DialogDescription>
            Paste the shared bearer token. Stored only in this browser&apos;s localStorage.
          </DialogDescription>
        </div>
        <form onSubmit={onSubmit} className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="token">App shared secret</Label>
            <Input
              id="token"
              type="password"
              autoFocus
              autoComplete="off"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder="••••••••••••"
            />
          </div>
          <Button type="submit" className="w-full" disabled={!value.trim()}>
            Unlock
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
