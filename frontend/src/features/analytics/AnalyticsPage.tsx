import BarChartOutlinedIcon from "@mui/icons-material/BarChartOutlined";
import FactCheckOutlinedIcon from "@mui/icons-material/FactCheckOutlined";
import PaymentsOutlinedIcon from "@mui/icons-material/PaymentsOutlined";
import ReceiptLongOutlinedIcon from "@mui/icons-material/ReceiptLongOutlined";
import RuleOutlinedIcon from "@mui/icons-material/RuleOutlined";
import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Skeleton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useQuery } from "@tanstack/react-query";
import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  type ChartData,
  type ChartOptions,
  Legend,
  LinearScale,
  Tooltip,
} from "chart.js";
import { useMemo, useState } from "react";
import { Bar } from "react-chartjs-2";
import { analyticsApi, getApiErrorMessage, type AnalyticsMonthlySpend, type CurrencyAmount } from "../../lib/api";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

const periodOptions = [3, 6, 12, 24];
const chartColors = ["#4057d6", "#007c78", "#a85d00", "#a34372", "#6f5dd5"];

function formatMoney({ amount, currency }: CurrencyAmount) {
  try {
    return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(amount);
  } catch {
    return `${currency} ${amount.toFixed(2)}`;
  }
}

function formatMonth(month: string) {
  const date = new Date(`${month}-01T00:00:00Z`);
  return Number.isNaN(date.getTime()) ? month : new Intl.DateTimeFormat("en-US", { month: "short", year: "numeric" }).format(date);
}

function titleCase(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

type MetricCardProps = {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  accent: "primary" | "success" | "warning" | "error";
};

function MetricCard({ label, value, icon, accent }: MetricCardProps) {
  return (
    <Card sx={{ height: "100%" }}>
      <CardContent sx={{ alignItems: "flex-start", display: "flex", gap: 1.5, p: 2.25, "&:last-child": { pb: 2.25 } }}>
        <Box sx={(theme) => ({ alignItems: "center", bgcolor: `${theme.palette[accent].main}1a`, borderRadius: 2, color: `${accent}.main`, display: "grid", flex: "0 0 auto", height: 42, placeItems: "center", width: 42 })}>
          {icon}
        </Box>
        <Box sx={{ minWidth: 0 }}>
          <Typography color="text.secondary" variant="body2">{label}</Typography>
          <Typography component="p" sx={{ fontSize: "1.55rem", fontWeight: 750, lineHeight: 1.35, mt: 0.35 }}>
            {value}
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
}

function monthlyChartData(rows: AnalyticsMonthlySpend[]): ChartData<"bar"> {
  const months = [...new Set(rows.map((row) => row.month))].sort();
  const currencies = [...new Set(rows.map((row) => row.currency))].sort();
  return {
    labels: months.map(formatMonth),
    datasets: currencies.map((currency, index) => ({
      label: currency,
      data: months.map((month) => rows.find((row) => row.month === month && row.currency === currency)?.amount ?? 0),
      backgroundColor: chartColors[index % chartColors.length],
      borderRadius: 6,
      maxBarThickness: 42,
    })),
  };
}

export function AnalyticsPage() {
  const [periodMonths, setPeriodMonths] = useState(6);
  const theme = useTheme();
  const analytics = useQuery({
    queryKey: ["analytics", "overview", periodMonths],
    queryFn: () => analyticsApi.overview(periodMonths),
  });
  const chartData = useMemo(() => monthlyChartData(analytics.data?.monthly_spend ?? []), [analytics.data?.monthly_spend]);
  const chartOptions = useMemo<ChartOptions<"bar">>(() => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: theme.palette.text.secondary, usePointStyle: true } },
      tooltip: {
        callbacks: {
          label: (context) => formatMoney({ amount: Number(context.raw ?? 0), currency: context.dataset.label ?? "USD" }),
        },
      },
    },
    scales: {
      x: { grid: { display: false }, ticks: { color: theme.palette.text.secondary } },
      y: { beginAtZero: true, grid: { color: theme.palette.divider }, ticks: { color: theme.palette.text.secondary } },
    },
  }), [theme]);
  const data = analytics.data;
  const totalRequested = data?.summary.total_requested ?? [];
  const scopeLabel = data?.scope === "organization" ? "Organization view" : data?.scope === "managed" ? "My managed work" : "My reports";

  return (
    <Box component="main" sx={{ margin: "0 auto", maxWidth: 1280, p: { xs: 2, sm: 3 } }}>
      <Stack spacing={3.25}>
        <Box sx={{ alignItems: { sm: "flex-end" }, display: "flex", flexDirection: { xs: "column", sm: "row" }, gap: 2, justifyContent: "space-between" }}>
          <Box>
            <Stack alignItems="center" direction="row" spacing={1}>
              <Typography color="primary" variant="overline">Operational analytics</Typography>
              {data && <Chip color="primary" label={scopeLabel} size="small" variant="outlined" />}
            </Stack>
            <Typography component="h1" sx={{ fontSize: { xs: "1.65rem", sm: "2rem" }, fontWeight: 800, letterSpacing: "-0.025em", mt: 0.25 }}>
              Reimbursement insights
            </Typography>
            <Typography color="text.secondary" sx={{ maxWidth: 700, mt: 0.75 }}>
              Track operational volume, policy signals, and reimbursement flow with privacy-safe aggregates.
            </Typography>
          </Box>
          <FormControl size="small" sx={{ minWidth: 170 }}>
            <InputLabel id="analytics-period-label">Reporting period</InputLabel>
            <Select
              id="analytics-period"
              label="Reporting period"
              labelId="analytics-period-label"
              onChange={(event) => setPeriodMonths(Number(event.target.value))}
              value={periodMonths}
            >
              {periodOptions.map((months) => <MenuItem key={months} value={months}>Last {months} months</MenuItem>)}
            </Select>
          </FormControl>
        </Box>

        {analytics.isError && <Alert severity="error">{getApiErrorMessage(analytics.error, "Unable to load reimbursement analytics.")}</Alert>}
        {analytics.isLoading && (
          <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))" }}>
            {Array.from({ length: 5 }, (_, index) => <Skeleton height={116} key={index} variant="rounded" />)}
          </Box>
        )}

        {data && (
          <>
            <Box sx={{ display: "grid", gap: 2, gridTemplateColumns: "repeat(auto-fit, minmax(205px, 1fr))" }}>
              <MetricCard accent="primary" icon={<ReceiptLongOutlinedIcon />} label="Reports in view" value={data.summary.report_count} />
              <MetricCard accent="warning" icon={<FactCheckOutlinedIcon />} label="Awaiting approval" value={data.summary.pending_approval_count} />
              <MetricCard accent="success" icon={<PaymentsOutlinedIcon />} label="Awaiting payment" value={data.summary.approved_pending_payment_count} />
              <MetricCard accent="error" icon={<RuleOutlinedIcon />} label="Policy flags" value={data.summary.policy_violation_count} />
              <MetricCard accent="primary" icon={<BarChartOutlinedIcon />} label="Requested amount" value={totalRequested.length === 1 ? formatMoney(totalRequested[0]) : `${totalRequested.length} currencies`} />
            </Box>

            <Box sx={{ display: "grid", gap: 2.5, gridTemplateColumns: { lg: "minmax(0, 1.6fr) minmax(320px, 0.9fr)" } }}>
              <Card>
                <CardContent sx={{ p: { xs: 2.25, sm: 3 }, "&:last-child": { pb: { xs: 2.25, sm: 3 } } }}>
                  <Typography component="h2" fontWeight={750} variant="h6">Monthly requested spend</Typography>
                  <Typography color="text.secondary" sx={{ mt: 0.5 }} variant="body2">Grouped by report currency. Totals are never converted or mixed across currencies.</Typography>
                  {chartData.labels?.length ? (
                    <Box sx={{ height: 300, mt: 2.5 }}>
                      <Bar aria-label="Monthly requested spend chart" data={chartData} options={chartOptions} role="img" />
                    </Box>
                  ) : (
                    <Alert severity="info" sx={{ mt: 2.5 }}>No report volume is available for this period.</Alert>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardContent sx={{ p: { xs: 2.25, sm: 3 }, "&:last-child": { pb: { xs: 2.25, sm: 3 } } }}>
                  <Typography component="h2" fontWeight={750} variant="h6">Workflow health</Typography>
                  <Stack divider={<Box sx={{ borderTop: 1, borderColor: "divider" }} />} spacing={0} sx={{ mt: 1.5 }}>
                    <Box sx={{ display: "flex", justifyContent: "space-between", py: 1.2 }}><Typography color="text.secondary">Average approval time</Typography><Typography fontWeight={700}>{data.summary.average_approval_hours === null || data.summary.average_approval_hours === undefined ? "—" : `${data.summary.average_approval_hours}h`}</Typography></Box>
                    <Box sx={{ display: "flex", justifyContent: "space-between", py: 1.2 }}><Typography color="text.secondary">Paid reports</Typography><Typography fontWeight={700}>{data.summary.paid_count}</Typography></Box>
                    <Box sx={{ display: "flex", justifyContent: "space-between", py: 1.2 }}><Typography color="text.secondary">Rejected reports</Typography><Typography fontWeight={700}>{data.summary.rejected_count}</Typography></Box>
                    <Box sx={{ display: "flex", justifyContent: "space-between", py: 1.2 }}><Typography color="text.secondary">Flagged line-item rate</Typography><Typography fontWeight={700}>{(data.summary.policy_violation_item_rate * 100).toFixed(1)}%</Typography></Box>
                  </Stack>
                </CardContent>
              </Card>
            </Box>

            <Box sx={{ display: "grid", gap: 2.5, gridTemplateColumns: { lg: "minmax(0, 1.05fr) minmax(0, 0.95fr)" } }}>
              <Card>
                <CardContent sx={{ p: 0, "&:last-child": { pb: 0 } }}>
                  <Box sx={{ p: { xs: 2.25, sm: 3 }, pb: 1.25 }}>
                    <Typography component="h2" fontWeight={750} variant="h6">Spend by category</Typography>
                    <Typography color="text.secondary" sx={{ mt: 0.5 }} variant="body2">Line-item totals are separated by currency.</Typography>
                  </Box>
                  <TableContainer>
                    <Table aria-label="Spend by category">
                      <TableHead><TableRow><TableCell>Category</TableCell><TableCell>Currency</TableCell><TableCell align="right">Amount</TableCell></TableRow></TableHead>
                      <TableBody>
                        {data.spending_by_category.length === 0 && <TableRow><TableCell colSpan={3}><Typography color="text.secondary" variant="body2">No category spending is available.</Typography></TableCell></TableRow>}
                        {data.spending_by_category.map((row) => <TableRow key={`${row.category}-${row.currency}`}><TableCell>{row.category}</TableCell><TableCell>{row.currency}</TableCell><TableCell align="right">{formatMoney(row)}</TableCell></TableRow>)}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </CardContent>
              </Card>

              <Card>
                <CardContent sx={{ p: { xs: 2.25, sm: 3 }, "&:last-child": { pb: { xs: 2.25, sm: 3 } } }}>
                  <Typography component="h2" fontWeight={750} variant="h6">Report status mix</Typography>
                  <Stack direction="row" flexWrap="wrap" gap={1} sx={{ mt: 2 }}>
                    {data.report_statuses.length === 0 && <Typography color="text.secondary" variant="body2">No report statuses are available.</Typography>}
                    {data.report_statuses.map((status) => <Chip key={status.status} label={`${titleCase(status.status)} · ${status.count}`} variant="outlined" />)}
                  </Stack>
                  <Alert icon={false} severity="info" sx={{ mt: 3 }}>
                    This dashboard contains only aggregate operational data. It does not display employee identities, receipt files, descriptions, or AI review detail.
                  </Alert>
                </CardContent>
              </Card>
            </Box>
          </>
        )}
      </Stack>
    </Box>
  );
}
