import { Search, SlidersHorizontal, X, Grid, List, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { SortOption } from "@/types";
import { MotionWrapper } from "@/components/motion/MotionWrapper";

type Props = {
  searchQuery: string;
  setSearchQuery: (v: string) => void;
  isDebouncing: boolean;
  showFilters: boolean;
  setShowFilters: (v: boolean) => void;
  activeFiltersCount: number;
  sortBy: SortOption;
  setSortBy: (v: SortOption) => void;
  viewMode: "grid" | "list";
  setViewMode: (v: "grid" | "list") => void;
};

export function FilterBar(props: Props) {
  const {
    searchQuery,
    setSearchQuery,
    isDebouncing,
    showFilters,
    setShowFilters,
    activeFiltersCount,
    sortBy,
    setSortBy,
    viewMode,
    setViewMode,
  } = props;

  return (
    <MotionWrapper
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={undefined}
      transition={{ duration: 0.3 }}
      whileInView={undefined}
      viewport={undefined}
      className="flex flex-col md:flex-row gap-4 mb-8"
    >
      <div className="relative flex-1">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
        <Input
          type="search"
          placeholder="Search by name, brand, or style..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-12 pr-12 h-12 text-base"
        />
        {searchQuery && (
          <button
            onClick={() => setSearchQuery("")}
            className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
          >
            <X className="h-5 w-5" />
          </button>
        )}
        {isDebouncing && (
          <div className="absolute right-12 top-1/2 -translate-y-1/2">
            <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          </div>
        )}
      </div>

      <div className="flex gap-2">
        <Button
          variant={showFilters ? "default" : "outline"}
          onClick={() => setShowFilters(!showFilters)}
          className="h-12"
        >
          <SlidersHorizontal className="h-4 w-4 mr-2" />
          Filters
          {activeFiltersCount > 0 && (
            <span className="ml-2 bg-accent text-accent-foreground text-xs rounded-full px-2 py-0.5">
              {activeFiltersCount}
            </span>
          )}
        </Button>

        <div className="relative">
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortOption)}
            className="h-12 px-4 pr-10 border border-input rounded-md bg-background text-foreground appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="relevance">Relevance</option>
            <option value="price-asc">Price: Low to High</option>
            <option value="price-desc">Price: High to Low</option>
            <option value="newest">Newest</option>
            <option value="popularity">Popularity</option>
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
        </div>

        <div className="hidden md:flex border border-input rounded-md overflow-hidden">
          <button
            onClick={() => setViewMode("grid")}
            className={`p-3 ${viewMode === "grid" ? "bg-muted" : "bg-background hover:bg-muted/50"}`}
          >
            <Grid className="h-4 w-4" />
          </button>
          <button
            onClick={() => setViewMode("list")}
            className={`p-3 ${viewMode === "list" ? "bg-muted" : "bg-background hover:bg-muted/50"}`}
          >
            <List className="h-4 w-4" />
          </button>
        </div>
      </div>
    </MotionWrapper>
  );
}

