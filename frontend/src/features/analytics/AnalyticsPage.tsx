import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Bar } from "react-chartjs-2";
import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  Tooltip,
} from "chart.js";
import { Select } from "../../components/ui/select";
import { LoadingState } from "../../components/ui/loading-state";
import {
  analyticsApi,
  getApiErrorMessage,
  type CurrencyAmount,
} from "../../lib/api";
ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);
const periods = [3, 6, 12, 24];
const colors = ["#ea2804", "#c01f00", "#e56a2b", "#ffad86"];
const money = ({ amount, currency }: CurrencyAmount) => {
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency,
    }).format(amount);
  } catch {
    return `${currency} ${amount.toFixed(2)}`;
  }
};
const title = (s: string) =>
  s.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
export function AnalyticsPage() {
  const [months, setMonths] = useState(6);
  const analytics = useQuery({
    queryKey: ["analytics", "overview", months],
    queryFn: () => analyticsApi.overview(months),
  });
  const data = analytics.data;
  const chart = useMemo(() => {
    const rows = data?.monthly_spend ?? [],
      labels = [...new Set(rows.map((r) => r.month))]
        .sort()
        .map((month) => new Date(`${month}-01T00:00:00Z`).toLocaleDateString("en-US", { month: "short", year: "numeric", timeZone: "UTC" })),
      currencies = [...new Set(rows.map((r) => r.currency))];
    return {
      labels,
      datasets: currencies.map((currency, i) => ({
        label: currency,
        data: labels.map(
          (month) =>
            rows.find((r) => new Date(`${r.month}-01T00:00:00Z`).toLocaleDateString("en-US", { month: "short", year: "numeric", timeZone: "UTC" }) === month && r.currency === currency)
              ?.amount ?? 0,
        ),
        backgroundColor: colors[i % colors.length],
        borderRadius: 6,
      })),
    };
  }, [data]);
  return (
    <main className="repl-page analytics-page">
      <header className="repl-page-head">
        <div>
          <p className="repl-eyebrow">Operational analytics</p>
          <h1 className="repl-title">Reimbursement insights.</h1>
          <p className="repl-lede">
            Track operational volume, policy signals, and reimbursement flow
            with privacy-safe aggregates.
          </p>
        </div>
        <label>
          Reporting period
          <Select
            onChange={(e) => setMonths(Number(e.target.value))}
            value={months}
          >
            {periods.map((p) => (
              <option key={p} value={p}>
                Last {p} months
              </option>
            ))}
          </Select>
        </label>
      </header>
      {analytics.isError && (
        <div className="repl-alert error">
          {getApiErrorMessage(
            analytics.error,
            "Unable to load reimbursement analytics.",
          )}
        </div>
      )}
      {analytics.isLoading && <LoadingState label="Loading analytics" />}
      {data && (
        <>
          <section className="metric-grid">
            {[
              ["Reports in view", data.summary.report_count],
              ["Awaiting approval", data.summary.pending_approval_count],
              ["Awaiting payment", data.summary.approved_pending_payment_count],
              ["Policy flags", data.summary.policy_violation_count],
              [
                "Requested amount",
                data.summary.total_requested.length === 1
                  ? money(data.summary.total_requested[0])
                  : `${data.summary.total_requested.length} currencies`,
              ],
            ].map(([label, value]) => (
              <article className="repl-card" key={String(label)}>
                <p>{label}</p>
                <strong>{value}</strong>
              </article>
            ))}
          </section>
          <section className="analytics-split">
            <article className="repl-card chart-card">
              <h2>Monthly requested spend</h2>
              <p>
                Grouped by report currency. Totals are never converted or mixed
                across currencies.
              </p>
              {chart.labels.length ? (
                <Bar
                  aria-label="Monthly requested spend chart"
                  data={chart}
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: "bottom" } },
                    scales: {
                      x: { grid: { display: false } },
                      y: { beginAtZero: true },
                    },
                  }}
                />
              ) : (
                <div className="repl-alert info">
                  No report volume is available for this period.
                </div>
              )}
            </article>
            <article className="repl-card health-card">
              <h2>Workflow health</h2>
              {[
                [
                  "Average approval time",
                  data.summary.average_approval_hours == null
                    ? "—"
                    : `${data.summary.average_approval_hours}h`,
                ],
                ["Paid reports", data.summary.paid_count],
                ["Rejected reports", data.summary.rejected_count],
                [
                  "Flagged line-item rate",
                  `${(data.summary.policy_violation_item_rate * 100).toFixed(1)}%`,
                ],
              ].map(([k, v]) => (
                <p key={String(k)}>
                  <span>{k}</span>
                  <b>{v}</b>
                </p>
              ))}
            </article>
          </section>
          <section className="analytics-split lower">
            <article className="repl-card table-card">
              <h2>Spend by category</h2>
              <table className="repl-table">
                <thead>
                  <tr>
                    <th>Category</th>
                    <th>Currency</th>
                    <th>Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {data.spending_by_category.map((row) => (
                    <tr key={`${row.category}-${row.currency}`}>
                      <td>{row.category}</td>
                      <td>{row.currency}</td>
                      <td>{money(row)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </article>
            <article className="repl-card status-card">
              <h2>Report status mix</h2>
              <div>
                {data.report_statuses.map((row) => (
                  <span className="pill" key={row.status}>
                    {title(row.status)} · {row.count}
                  </span>
                ))}
              </div>
              <p className="repl-alert info">
                This dashboard contains only aggregate operational data. It does
                not display employee identities, receipt files, descriptions, or
                AI review detail.
              </p>
            </article>
          </section>
        </>
      )}
    </main>
  );
}
