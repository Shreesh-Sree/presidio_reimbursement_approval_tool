import { useEffect, useRef } from "react";
import { supabase } from "./supabase";

export const IDLE_TIMEOUT_MS = 30 * 60 * 1000;
export const CHECK_INTERVAL_MS = 60 * 1000;
export const SESSION_CHECK_TIMEOUT_MS = 10 * 1000;

export function useSessionKeepAlive(onIdle: () => void | Promise<void>) {
  const lastActivity = useRef(Date.now());
  const sessionCheckInFlight = useRef(false);

  useEffect(() => {
    const markActive = () => {
      lastActivity.current = Date.now();
    };

    const events = ["mousemove", "keydown", "click", "scroll", "touchstart"] as const;
    for (const event of events) {
      window.addEventListener(event, markActive, { passive: true });
    }

    let idleHandled = false;
    const handleIdle = () => {
      if (idleHandled) return;
      idleHandled = true;
      clearInterval(interval);
      void Promise.resolve(onIdle()).catch(() => undefined);
    };

    const checkSession = async () => {
      if (sessionCheckInFlight.current) return;
      sessionCheckInFlight.current = true;
      const request = Promise.resolve().then(() => supabase.auth.getSession());
      void request.then(
        () => { sessionCheckInFlight.current = false; },
        () => { sessionCheckInFlight.current = false; },
      );

      let timeoutId: number | undefined;
      const deadline = new Promise<"timed_out">((resolve) => {
        timeoutId = window.setTimeout(() => resolve("timed_out"), SESSION_CHECK_TIMEOUT_MS);
      });
      const outcome = await Promise.race([
        request.then(() => "complete" as const, () => "complete" as const),
        deadline,
      ]);

      // A timed-out Supabase call cannot be aborted by this SDK API. Keep the
      // in-flight guard set until it settles, rather than start overlapping
      // checks every minute during an outage.
      if (outcome === "complete" && timeoutId !== undefined) clearTimeout(timeoutId);
    };

    const interval = setInterval(() => {
      const idle = Date.now() - lastActivity.current;
      if (idle >= IDLE_TIMEOUT_MS) {
        handleIdle();
        return;
      }
      void checkSession();
    }, CHECK_INTERVAL_MS);

    return () => {
      for (const event of events) {
        window.removeEventListener(event, markActive);
      }
      clearInterval(interval);
    };
  }, [onIdle]);
}
