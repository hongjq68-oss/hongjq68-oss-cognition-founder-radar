import { createContext, useContext } from "react";
import type { Any } from "./api";

export type Me = { id: number; name: string; email: string; role: string; permissions: string[] };
export const AppCtx = createContext<{ me: Me; meta: Any; can: (p: string) => boolean; toast: (m: string, kind?: "error" | "ok") => void }>(null as never);
export const useApp = () => useContext(AppCtx);
