import { useState, type ReactNode } from "react";
import { useMutation } from "@tanstack/react-query";
import { attachmentsApi, getApiErrorMessage } from "../lib/api";
import { Button } from "./ui/button";

type AuthenticatedAttachmentLinkProps = {
  url: string;
  children: ReactNode;
  className?: string;
};

function isApiManagedUrl(url: string) {
  return url.startsWith("/");
}

/**
 * Opens core-managed attachments through the authenticated API client.  A
 * regular browser anchor cannot attach the user's bearer token, so it would
 * otherwise fail for protected receipts and policy documents.
 */
export function AuthenticatedAttachmentLink({ url, children, className }: AuthenticatedAttachmentLinkProps) {
  const [error, setError] = useState<string | null>(null);
  const openAttachment = useMutation({
    mutationFn: () => attachmentsApi.download(url),
    onMutate: () => setError(null),
    onSuccess: (blob) => {
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.target = "_blank";
      link.rel = "noreferrer";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
    },
    onError: (requestError) => setError(getApiErrorMessage(requestError, "Unable to open this protected file.")),
  });

  if (!isApiManagedUrl(url)) {
    return <a className={className} href={url} rel="noreferrer" target="_blank">{children}</a>;
  }

  return (
    <span className="inline-flex flex-col items-start gap-1">
      <Button
        className={className}
        disabled={openAttachment.isPending}
        onClick={() => openAttachment.mutate()}
        variant="ghost"
      >
        {openAttachment.isPending ? "Opening…" : children}
      </Button>
      {error && <span className="text-sm text-rose-600" role="alert">{error}</span>}
    </span>
  );
}
