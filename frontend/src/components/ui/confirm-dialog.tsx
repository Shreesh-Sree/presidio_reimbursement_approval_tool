import { Button } from "./button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "./dialog";

export function ConfirmDialog({ confirmLabel = "Delete", description, onConfirm, onOpenChange, open, title }: { confirmLabel?: string; description: string; onConfirm: () => void; onOpenChange: (open: boolean) => void; open: boolean; title: string }) {
  return <Dialog onOpenChange={onOpenChange} open={open}><DialogContent><DialogTitle>{title}</DialogTitle><DialogDescription>{description}</DialogDescription><div className="mt-6 flex justify-end gap-2"><Button onClick={() => onOpenChange(false)} variant="outline">Cancel</Button><Button onClick={onConfirm} variant="destructive">{confirmLabel}</Button></div></DialogContent></Dialog>;
}
