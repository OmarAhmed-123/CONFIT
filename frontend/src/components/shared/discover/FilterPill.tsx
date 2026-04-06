import { X } from "lucide-react";

type Props = {
  label: string;
  onRemove: () => void;
};

export function FilterPill({ label, onRemove }: Props) {
  return (
    <span className="inline-flex items-center gap-1 bg-muted text-sm px-3 py-1 rounded-full">
      {label}
      <button onClick={onRemove} className="hover:text-destructive" aria-label={`Remove ${label}`}>
        <X className="h-3 w-3" />
      </button>
    </span>
  );
}

