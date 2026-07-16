import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bell } from "@phosphor-icons/react";
import { notificationsApi } from "../../lib/api";
import { NotificationFeed } from "./NotificationFeed";

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const notifications = useQuery({
    queryKey: ["notifications"],
    queryFn: notificationsApi.list,
    refetchInterval: 30_000,
  });
  const unreadCount = notifications.data?.filter((notification) => !notification.read_at).length ?? 0;
  const label = unreadCount > 0 ? `${unreadCount} unread notifications` : "Notifications";

  return (
    <div className="relative">
      <button
        aria-expanded={open}
        aria-label={label}
        className="relative inline-flex size-10 items-center justify-center rounded-md text-xl text-slate-700 transition hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 dark:text-slate-200 dark:hover:bg-slate-800"
        onClick={() => setOpen((current) => !current)}
        type="button"
      >
        <Bell aria-hidden size={20} weight="bold" />
        {unreadCount > 0 && <span className="absolute -right-1 -top-1 inline-flex min-w-5 items-center justify-center rounded-full bg-rose-600 px-1 text-xs font-semibold text-white">{unreadCount > 99 ? "99+" : unreadCount}</span>}
      </button>
      {open && (
        <section aria-label="Notification feed" className="absolute right-0 z-30 mt-2 w-[min(24rem,calc(100vw-2rem))] overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl dark:border-slate-800 dark:bg-slate-900">
          <header className="flex items-center justify-between border-b border-slate-200 px-4 py-3 dark:border-slate-800">
            <h2 className="font-semibold text-slate-950 dark:text-white">Notifications</h2>
            {notifications.isFetching && <span className="text-xs text-slate-500 dark:text-slate-400">Updating…</span>}
          </header>
          {notifications.isError ? <p className="p-4 text-sm text-rose-600">Unable to load notifications.</p> : <NotificationFeed notifications={notifications.data ?? []} />}
        </section>
      )}
    </div>
  );
}
