import React from "react";
import { Eye, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Product } from "@/types";
import { Badge } from "@/components/ui/badge";

export type OutfitItemPosition = "top" | "bottom" | "shoes" | "accessory";

export type OutfitItem = {
  position: OutfitItemPosition;
  product: Product;
};

export type OutfitBuild = {
  id: string;
  name: string;
  confidence: number;
  styleScore: number;
  image: string;
  priceEstimate: number;
  budgetMax?: number | null;
  remaining?: number | null;
  styleExplanation: string;
  items: Record<OutfitItemPosition, OutfitItem>;
};

const positionLabels: Record<OutfitItemPosition, string> = {
  top: "Top",
  bottom: "Bottom",
  shoes: "Shoes",
  accessory: "Accessory",
};

function formatDollars(value: number) {
  try {
    return value.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
  } catch {
    return `$${Math.round(value)}`;
  }
}

function budgetStatusClass(remaining: number | null | undefined) {
  if (remaining == null) return "bg-card/60 border-border/60 text-muted-foreground";
  if (remaining >= 0) return "bg-success/10 border-success/20 text-success";
  return "bg-destructive/10 border-destructive/20 text-destructive";
}

export function OutfitCard({
  outfit,
  onTryOn,
  onReplaceItem,
  onViewProduct,
  className,
}: {
  outfit: OutfitBuild;
  onTryOn: (outfitId: string, focus?: OutfitItemPosition) => void;
  onReplaceItem: (outfitId: string, position: OutfitItemPosition) => void;
  onViewProduct: (productId: string) => void;
  className?: string;
}) {
  const remaining = outfit.remaining ?? null;

  return (
    <article className={cn("glass-panel rounded-3xl border-white/10 overflow-hidden", className)}>
      <div className="relative">
        <div className="aspect-[16/10] bg-muted overflow-hidden">
          <img
            src={outfit.image}
            alt={outfit.name}
            loading="lazy"
            decoding="async"
            className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent" />
        </div>

        <div className="absolute top-3 left-3 right-3 flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="bg-accent/85 text-accent-foreground border-white/10">
              {outfit.styleScore}% match
            </Badge>
            <Badge variant="outline" className="border-white/10 bg-card/30 text-foreground">
              {formatDollars(outfit.priceEstimate)}
            </Badge>
          </div>
          {outfit.budgetMax != null && (
            <div
              className={cn(
                "inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold backdrop-blur-md",
                budgetStatusClass(remaining)
              )}
            >
              {remaining >= 0 ? "Within budget" : "Over budget"}
            </div>
          )}
        </div>
      </div>

      <div className="p-4 md:p-5 space-y-3">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="font-semibold tracking-tight">{outfit.name}</h3>
            <p className="mt-1 text-xs text-muted-foreground">
              {outfit.confidence >= 85 ? "High-confidence styling" : "Carefully curated"}
            </p>
          </div>
          <div className="text-right">
            {outfit.budgetMax != null ? (
              <div className="text-xs text-muted-foreground">
                Budget: <span className="font-semibold text-foreground">{formatDollars(outfit.budgetMax)}</span>
                <div className="mt-1 flex items-center gap-2">
                  <span
                    className={cn(
                      "h-1.5 rounded-full bg-white/10 w-28 overflow-hidden border border-white/10",
                      remaining != null && remaining >= 0 ? "shadow-[0_0_30px_rgba(74,222,128,0.15)]" : "shadow-[0_0_30px_rgba(248,113,113,0.15)]"
                    )}
                  >
                    <span
                      className={cn(
                        "block h-full",
                        remaining != null && remaining >= 0 ? "bg-success" : "bg-destructive"
                      )}
                      style={{
                        width: `${Math.min(100, Math.max(0, (outfit.priceEstimate / Math.max(1, outfit.budgetMax)) * 100))}%`,
                        transition: "width 400ms cubic-bezier(0.25,0.46,0.45,0.94)",
                      }}
                    />
                  </span>
                </div>
                <div className="mt-2 text-[11px]">
                  {remaining == null ? null : remaining >= 0 ? (
                    <span className="text-success font-semibold">Remaining {formatDollars(remaining)}</span>
                  ) : (
                    <span className="text-destructive font-semibold">Over {formatDollars(Math.abs(remaining))}</span>
                  )}
                </div>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">Budget-aware suggestions</p>
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-border/60 bg-background/30 p-3">
          <p className="text-xs font-medium text-foreground">Style explanation</p>
          <p className="mt-1 text-body-sm text-muted-foreground">{outfit.styleExplanation}</p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          {(
            [
              ["top", outfit.items.top],
              ["bottom", outfit.items.bottom],
              ["shoes", outfit.items.shoes],
              ["accessory", outfit.items.accessory],
            ] as Array<[OutfitItemPosition, OutfitItem]>
          ).map(([pos, item]) => (
            <div
              key={pos}
              className="group relative rounded-2xl border border-white/10 bg-card/20 overflow-hidden"
            >
              <div className="aspect-[4/3] bg-muted overflow-hidden">
                <img
                  src={item.product.images?.[0] || outfit.image}
                  alt={item.product.name}
                  loading="lazy"
                  decoding="async"
                  className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/10 to-transparent opacity-90 group-hover:opacity-70 transition-opacity duration-300" />
              </div>

              <div className="absolute left-3 right-3 bottom-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-[11px] font-semibold text-white/80">{positionLabels[pos]}</p>
                    <p className="text-sm font-semibold text-white leading-tight line-clamp-1">
                      {item.product.name}
                    </p>
                  </div>
                  <p className="text-xs font-semibold text-white/90 whitespace-nowrap">
                    {formatDollars(item.product.price)}
                  </p>
                </div>
              </div>

              <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-end p-3">
                <div className="w-full flex gap-2">
                  <button
                    type="button"
                    className="flex-1 rounded-full bg-background/85 border border-white/15 text-foreground px-3 py-2 text-xs font-semibold hover:bg-background transition-colors"
                    onClick={() => onTryOn(outfit.id, pos)}
                  >
                    <span className="inline-flex items-center justify-center gap-1">
                      <Eye className="h-3.5 w-3.5" />
                      Try
                    </span>
                  </button>
                  <button
                    type="button"
                    className="w-10 rounded-full bg-accent/25 border border-white/15 text-accent-foreground px-0 py-2 text-xs font-semibold hover:bg-accent/30 transition-colors"
                    aria-label={`Replace ${positionLabels[pos]}`}
                    onClick={() => onReplaceItem(outfit.id, pos)}
                  >
                    <span className="inline-flex items-center justify-center">
                      <RefreshCw className="h-4 w-4 text-accent" />
                    </span>
                  </button>
                  <button
                    type="button"
                    className="w-10 rounded-full bg-background/85 border border-white/15 text-foreground px-0 py-2 text-xs font-semibold hover:bg-background transition-colors"
                    aria-label={`View product ${item.product.name}`}
                    onClick={() => onViewProduct(item.product.id)}
                  >
                    <span className="inline-flex items-center justify-center text-white/90">
                      <span className="text-[14px] leading-none font-bold">↗</span>
                    </span>
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </article>
  );
}

