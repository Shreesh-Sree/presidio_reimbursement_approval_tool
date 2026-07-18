import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button } from "../../components/ui/button";
import { getApiErrorMessage, apiClient } from "../../lib/api";

interface AccessRequest {
  id: string;
  email: string;
  full_name: string;
  requested_at: string;
  status: string;
}

interface Department {
  id: string;
  name: string;
}

export function AccessRequestsPage() {
  const queryClient = useQueryClient();
  const [selectedDepartments, setSelectedDepartments] = useState<Record<string, string>>({});

  const { data: requests = [], isLoading } = useQuery({
    queryKey: ["access-requests"],
    queryFn: async () => {
      const response = await apiClient.get<AccessRequest[]>("/access-requests");
      return response.data;
    },
  });

  const { data: departments = [] } = useQuery({
    queryKey: ["departments"],
    queryFn: async () => {
      const response = await apiClient.get<Department[]>("/departments");
      return response.data;
    },
  });

  const approveMutation = useMutation({
    mutationFn: async ({ requestId, departmentId }: { requestId: string; departmentId: string }) => {
      const response = await apiClient.post(`/access-requests/${requestId}/approve`, {
        department_id: departmentId,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["access-requests"] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: async (requestId: string) => {
      const response = await apiClient.post(`/access-requests/${requestId}/reject`, {});
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["access-requests"] });
    },
  });

  if (isLoading) {
    return <div className="p-6">Loading...</div>;
  }

  if (requests.length === 0) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-semibold mb-6">Access Requests</h1>
        <div className="rounded-lg border border-dashed border-slate-300 p-12 text-center dark:border-slate-700">
          <p className="text-slate-600 dark:text-slate-400">No pending access requests</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold mb-6">Access Requests ({requests.length})</h1>

      <div className="space-y-4">
        {requests.map((request) => (
          <div
            key={request.id}
            className="rounded-lg border border-slate-200 bg-white p-6 dark:border-slate-700 dark:bg-slate-800"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h3 className="text-lg font-medium">{request.full_name}</h3>
                <p className="text-sm text-slate-600 dark:text-slate-400">{request.email}</p>
                <p className="mt-2 text-xs text-slate-500">
                  Requested: {new Date(request.requested_at).toLocaleString()}
                </p>
              </div>

              <div className="flex items-center gap-3">
                <select
                  value={selectedDepartments[request.id] || ""}
                  onChange={(e) =>
                    setSelectedDepartments({ ...selectedDepartments, [request.id]: e.target.value })
                  }
                  className="rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-700"
                >
                  <option value="">Select Department</option>
                  {departments.map((dept) => (
                    <option key={dept.id} value={dept.id}>
                      {dept.name}
                    </option>
                  ))}
                </select>

                <Button
                  onClick={() =>
                    approveMutation.mutate({
                      requestId: request.id,
                      departmentId: selectedDepartments[request.id],
                    })
                  }
                  disabled={!selectedDepartments[request.id] || approveMutation.isPending}
                  variant="default"
                >
                  Approve
                </Button>

                <Button
                  onClick={() => rejectMutation.mutate(request.id)}
                  disabled={rejectMutation.isPending}
                  variant="outline"
                >
                  Reject
                </Button>
              </div>
            </div>

            {approveMutation.isError && (
              <p className="mt-2 text-sm text-red-600">{approveMutation.error.message}</p>
            )}
            {rejectMutation.isError && (
              <p className="mt-2 text-sm text-red-600">{rejectMutation.error.message}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
