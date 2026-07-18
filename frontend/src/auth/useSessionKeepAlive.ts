import { useEffect, useRef } from "react";
import { supabase } from "./supabase";

const IDLE_TIMEOUT_MS = 30 * 60 * 1000;
const CHECK_INTERVAL_MS = 60 * 1000;

export function useSessionKeepAlive(onIdle: () => void) {
  const lastActivity = useRef(Date.now());

  useEffect(() => {
    const markActive = () => {
      lastActivity.current = Date.now();
    };

    const events = ["mousemove", "keydown", "click", "scroll", "touchstart"] as const;
    for (const event of events) {
      window.addEventListener(event, markActive, { passive: true });
    }

    const interval = setInterval(async () => {
      const idle = Date.now() - lastActivity.current;
      if (idle >= IDLE_TIMEOUT_MS) {
        clearInterval(interval);
        onIdle();
        return;
      }
      await supabase.auth.getSession();
    }, CHECK_INTERVAL_MS);

    return () => {
      for (const event of events) {
        window.removeEventListener(event, markActive);
      }
      clearInterval(interval);
    };
  }, [onIdle]);
}
