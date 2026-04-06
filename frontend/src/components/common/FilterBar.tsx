import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Filter, X, ChevronDown, SlidersHorizontal } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet';
import { Slider } from '@/components/ui/slider';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';

interface FilterOption {
  id: string;
  label: string;
  count?: number;
}

interface FilterGroup {
  id: string;
  label: string;
  type: 'single' | 'multi' | 'range';
  options: FilterOption[];
  min?: number;
  max?: number;
}

interface FilterBarProps {
  groups: FilterGroup[];
  selectedFilters: Record<string, string[]>;
  onFilterChange: (groupId: string, values: string[]) => void;
  onClearAll: () => void;
  searchPlaceholder?: string;
  onSearch?: (query: string) => void;
  sortOptions?: { value: string; label: string }[];
  onSortChange?: (value: string) => void;
  className?: string;
}

export function FilterBar({
  groups,
  selectedFilters,
  onFilterChange,
  onClearAll,
  searchPlaceholder = 'Search...',
  onSearch,
  sortOptions,
  onSortChange,
  className,
}: FilterBarProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [isMobileFilterOpen, setIsMobileFilterOpen] = useState(false);

  const totalFilters = Object.values(selectedFilters).flat().length;

  const handleSearch = (value: string) => {
    setSearchQuery(value);
    onSearch?.(value);
  };

  const FilterContent = () => (
    <div className="space-y-6">
      {groups.map((group) => (
        <div key={group.id} className="space-y-3">
          <h3 className="font-medium">{group.label}</h3>
          
          {group.type === 'multi' && (
            <div className="flex flex-wrap gap-2">
              {group.options.map((option) => (
                <Badge
                  key={option.id}
                  variant={selectedFilters[group.id]?.includes(option.id) ? 'default' : 'outline'}
                  className="cursor-pointer"
                  onClick={() => {
                    const current = selectedFilters[group.id] || [];
                    const newValues = current.includes(option.id)
                      ? current.filter((v) => v !== option.id)
                      : [...current, option.id];
                    onFilterChange(group.id, newValues);
                  }}
                >
                  {option.label}
                  {option.count !== undefined && (
                    <span className="ml-1 text-xs opacity-70">({option.count})</span>
                  )}
                </Badge>
              ))}
            </div>
          )}
          
          {group.type === 'single' && (
            <Select
              value={selectedFilters[group.id]?.[0]}
              onValueChange={(value) => onFilterChange(group.id, [value])}
            >
              <SelectTrigger>
                <SelectValue placeholder={`Select ${group.label.toLowerCase()}`} />
              </SelectTrigger>
              <SelectContent>
                {group.options.map((option) => (
                  <SelectItem key={option.id} value={option.id}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          
          {group.type === 'range' && group.min !== undefined && group.max !== undefined && (
            <div className="space-y-4">
              <Slider
                min={group.min}
                max={group.max}
                value={[
                  Number(selectedFilters[group.id]?.[0]) || group.min,
                  Number(selectedFilters[group.id]?.[1]) || group.max,
                ]}
                onValueChange={(value) => onFilterChange(group.id, value.map(String))}
              />
              <div className="flex justify-between text-sm text-muted-foreground">
                <span>${group.min}</span>
                <span>${group.max}</span>
              </div>
            </div>
          )}
          
          <Separator />
        </div>
      ))}
      
      {totalFilters > 0 && (
        <Button variant="outline" className="w-full" onClick={onClearAll}>
          Clear All Filters
        </Button>
      )}
    </div>
  );

  return (
    <div className={cn('space-y-4', className)}>
      {/* Desktop Filter Bar */}
      <div className="hidden lg:flex items-center gap-4">
        {/* Search */}
        {onSearch && (
          <div className="relative flex-1 max-w-md">
            <Input
              placeholder={searchPlaceholder}
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              className="pr-8"
            />
            {searchQuery && (
              <Button
                size="icon"
                variant="ghost"
                className="absolute right-1 top-1/2 -translate-y-1/2 h-6 w-6"
                onClick={() => handleSearch('')}
              >
                <X className="h-3 w-3" />
              </Button>
            )}
          </div>
        )}

        {/* Filter Dropdowns */}
        <div className="flex items-center gap-2">
          {groups.slice(0, 3).map((group) => (
            group.type === 'multi' && (
              <Select
                key={group.id}
                value={selectedFilters[group.id]?.[0]}
                onValueChange={(value) => {
                  const current = selectedFilters[group.id] || [];
                  onFilterChange(group.id, current.includes(value) ? [] : [value]);
                }}
              >
                <SelectTrigger className="w-32">
                  <SelectValue placeholder={group.label} />
                </SelectTrigger>
                <SelectContent>
                  {group.options.map((option) => (
                    <SelectItem key={option.id} value={option.id}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )
          ))}
        </div>

        {/* Sort */}
        {sortOptions && onSortChange && (
          <Select onValueChange={onSortChange}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              {sortOptions.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}

        {/* More Filters */}
        <Sheet open={isMobileFilterOpen} onOpenChange={setIsMobileFilterOpen}>
          <SheetTrigger asChild>
            <Button variant="outline" className="relative">
              <SlidersHorizontal className="mr-2 h-4 w-4" />
              Filters
              {totalFilters > 0 && (
                <Badge className="absolute -right-2 -top-2 h-5 w-5 rounded-full p-0 text-xs">
                  {totalFilters}
                </Badge>
              )}
            </Button>
          </SheetTrigger>
          <SheetContent>
            <SheetHeader>
              <SheetTitle>Filters</SheetTitle>
            </SheetHeader>
            <div className="mt-6">
              <FilterContent />
            </div>
          </SheetContent>
        </Sheet>
      </div>

      {/* Mobile Filter Bar */}
      <div className="lg:hidden flex items-center gap-2">
        {onSearch && (
          <Input
            placeholder={searchPlaceholder}
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            className="flex-1"
          />
        )}
        <Sheet open={isMobileFilterOpen} onOpenChange={setIsMobileFilterOpen}>
          <SheetTrigger asChild>
            <Button variant="outline" size="icon" className="relative">
              <Filter className="h-4 w-4" />
              {totalFilters > 0 && (
                <Badge className="absolute -right-2 -top-2 h-5 w-5 rounded-full p-0 text-xs">
                  {totalFilters}
                </Badge>
              )}
            </Button>
          </SheetTrigger>
          <SheetContent side="right">
            <SheetHeader>
              <SheetTitle>Filters</SheetTitle>
            </SheetHeader>
            <div className="mt-6">
              <FilterContent />
            </div>
          </SheetContent>
        </Sheet>
      </div>

      {/* Active Filters */}
      <AnimatePresence>
        {totalFilters > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="flex flex-wrap gap-2"
          >
            {Object.entries(selectedFilters).map(([groupId, values]) => {
              const group = groups.find((g) => g.id === groupId);
              return values.map((value) => {
                const option = group?.options.find((o) => o.id === value);
                return (
                  <Badge
                    key={`${groupId}-${value}`}
                    variant="secondary"
                    className="cursor-pointer"
                    onClick={() => {
                      const newValues = values.filter((v) => v !== value);
                      onFilterChange(groupId, newValues);
                    }}
                  >
                    {option?.label || value}
                    <X className="ml-1 h-3 w-3" />
                  </Badge>
                );
              });
            })}
            <Button
              variant="ghost"
              size="sm"
              className="text-xs"
              onClick={onClearAll}
            >
              Clear all
            </Button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
