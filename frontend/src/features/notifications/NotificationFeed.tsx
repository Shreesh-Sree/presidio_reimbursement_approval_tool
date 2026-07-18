import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { notificationsApi, type Notification } from "../../lib/api";

type NotificationFeedProps = {
  notifications: Notification[];
};

function relativeTimestamp(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleString();
}

export function NotificationFeed({ notifications }: NotificationFeedProps) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const markRead = useMutation({
    mutationFn: (notificationId: string) => notificationsApi.markRead(notificationId),
    onSuccess: (updatedNotification) => {
      queryClient.setQueryData<Notification[]>(["notifications"], (current) =>
        current?.map((notification) => notification.id === updatedNotification.id ? { ...notification, ...updatedNotification, read_at: updatedNotification.read_at ?? new Date().toISOString() } : notification) ?? [],
      );
    },
  });

  if (notifications.length === 0) {
    return <p className="p-4 text-sm text-slate-600 dark:text-slate-300">You are all caught up.</p>;
  }

  return (
    <ul className="divide-y divide-slate-200 dark:divide-slate-800">
      {notifications.map((notification) => {
        const unread = !notification.read_at;
        return (
          <li key={notification.id}>
            <button
              className={unread ? "w-full bg-orange-50 px-4 py-3 text-left transition hover:bg-orange-100 dark:bg-orange-950/40 dark:hover:bg-orange-950/60" : "w-full px-4 py-3 text-left transition hover:bg-slate-50 dark:hover:bg-slate-800"}
              disabled={markRead.isPending}
              onClick={() => {
                if (unread) markRead.mutate(notification.id);
                if (notification.report_id) {
                  navigate(`/reports/${notification.report_id}`);
                }
              }}
              type="button"
            >
              <span className="flex items-start gap-2">
                {unread && <span aria-label="Unread" className="mt-1.5 size-2 shrink-0 rounded-full bg-orange-600 dark:bg-orange-400" />}
                <span className="min-w-0">
                  <span className="block text-sm font-medium text-slate-950 dark:text-white">{notification.title}</span>
                  {notification.body && <span className="mt-1 block text-sm text-slate-600 dark:text-slate-300">{notification.body}</span>}
                  <span className="mt-1 block text-xs text-slate-500 dark:text-slate-400">{relativeTimestamp(notification.created_at)}</span>
                </span>
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
