import { useQuery } from "@tanstack/react-query";
import { type OrgChartNode, userAdminApi } from "./api";
import { LoadingState } from "../../components/ui/loading-state";

function labelForRole(role: string) {
  return role.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function OrgChartBranch({ node, level, ancestors }: { node: OrgChartNode; level: number; ancestors: Set<string> }) {
  const introducesCycle = ancestors.has(node.id);
  const nextAncestors = new Set(ancestors);
  nextAncestors.add(node.id);

  return (
    <li aria-level={level} className="space-y-3" role="treeitem">
      <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="font-semibold text-slate-950 dark:text-white">{node.name}</h2>
            {node.email && <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">{node.email}</p>}
          </div>
          <div className="flex flex-wrap gap-1">
            {node.roles.length > 0 ? node.roles.map((role) => (
              <span className="rounded-full bg-orange-50 px-2 py-0.5 text-xs font-medium text-orange-700 dark:bg-orange-950/50 dark:text-orange-200" key={role}>
                {labelForRole(role)}
              </span>
            )) : <span className="text-xs text-slate-500 dark:text-slate-400">No roles assigned</span>}
          </div>
        </div>
        <p className="mt-3 text-sm text-slate-600 dark:text-slate-300">
          {node.reports.length} {node.reports.length === 1 ? "direct report" : "direct reports"}
        </p>
        {introducesCycle && <p className="mt-2 text-sm text-amber-700 dark:text-amber-300">This reporting relationship was not expanded because it repeats a user in the current path.</p>}
      </article>

      {!introducesCycle && node.reports.length > 0 && (
        <ul className="ml-3 space-y-3 border-l border-slate-200 pl-4 dark:border-slate-700 sm:ml-6 sm:pl-6" role="group">
          {node.reports.map((report) => (
            <OrgChartBranch ancestors={nextAncestors} key={report.id} level={level + 1} node={report} />
          ))}
        </ul>
      )}
    </li>
  );
}

export function OrgChartPage() {
  const orgChart = useQuery({ queryKey: ["org-chart"], queryFn: userAdminApi.orgChart });

  return (
    <main className="mx-auto w-full max-w-5xl space-y-6 p-4 sm:p-6">
      <header className="border-b border-slate-200 pb-5 dark:border-slate-800">
        <p className="text-sm font-medium text-orange-600 dark:text-orange-400">Administration</p>
        <h1 className="mt-1 text-2xl font-semibold text-slate-950 dark:text-white">Organization chart</h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">View reporting lines and the roles assigned to each person.</p>
      </header>

      {orgChart.isLoading && <LoadingState label="Loading organization chart" />}
      {orgChart.isError && <p className="rounded-md bg-orange-50 p-3 text-sm text-orange-700 dark:bg-orange-950/40 dark:text-orange-200">Unable to load the organization chart.</p>}
      {orgChart.data?.length === 0 && (
        <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center text-sm text-slate-600 dark:border-slate-700 dark:text-slate-300">
          No reporting relationships have been configured yet.
        </div>
      )}

      <ul aria-label="Organization hierarchy" className="space-y-3" role="tree">
        {orgChart.data?.map((node) => <OrgChartBranch ancestors={new Set()} key={node.id} level={1} node={node} />)}
      </ul>
    </main>
  );
}
