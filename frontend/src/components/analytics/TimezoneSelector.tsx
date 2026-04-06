/**
 * CONFIT — Timezone Selector Component
 * ======================================
 * Dropdown for selecting timezone for analytics display.
 * Persists preference to localStorage and syncs with store.
 */

import { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Globe, Check, ChevronDown } from 'lucide-react';

interface TimezoneSelectorProps {
  value?: string;
  onChange?: (timezone: string) => void;
  className?: string;
}

// Common timezones for business analytics
const TIMEZONES = [
  { value: 'UTC', label: 'UTC', offset: '+00:00' },
  { value: 'America/New_York', label: 'Eastern Time', offset: 'UTC-5/-4' },
  { value: 'America/Chicago', label: 'Central Time', offset: 'UTC-6/-5' },
  { value: 'America/Denver', label: 'Mountain Time', offset: 'UTC-7/-6' },
  { value: 'America/Los_Angeles', label: 'Pacific Time', offset: 'UTC-8/-7' },
  { value: 'America/Sao_Paulo', label: 'São Paulo', offset: 'UTC-3' },
  { value: 'Europe/London', label: 'London', offset: 'UTC+0/+1' },
  { value: 'Europe/Paris', label: 'Paris', offset: 'UTC+1/+2' },
  { value: 'Europe/Berlin', label: 'Berlin', offset: 'UTC+1/+2' },
  { value: 'Asia/Dubai', label: 'Dubai', offset: 'UTC+4' },
  { value: 'Asia/Kolkata', label: 'Mumbai', offset: 'UTC+5:30' },
  { value: 'Asia/Bangkok', label: 'Bangkok', offset: 'UTC+7' },
  { value: 'Asia/Singapore', label: 'Singapore', offset: 'UTC+8' },
  { value: 'Asia/Tokyo', label: 'Tokyo', offset: 'UTC+9' },
  { value: 'Australia/Sydney', label: 'Sydney', offset: 'UTC+10/+11' },
];

const STORAGE_KEY = 'confit-analytics-timezone';

export function TimezoneSelector({
  value,
  onChange,
  className = '',
}: TimezoneSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [selected, setSelected] = useState<string>(() => {
    // Priority: prop > localStorage > browser > UTC
    if (value) return value;
    
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) return stored;
    
    // Try to detect browser timezone
    try {
      const browserTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      if (TIMEZONES.some((tz) => tz.value === browserTz)) {
        return browserTz;
      }
    } catch {
      // Ignore
    }
    
    return 'UTC';
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, selected);
    onChange?.(selected);
  }, [selected, onChange]);

  const selectedTimezone = useMemo(
    () => TIMEZONES.find((tz) => tz.value === selected) || TIMEZONES[0],
    [selected]
  );

  const formatTimeInTimezone = (timezone: string): string => {
    try {
      return new Date().toLocaleTimeString('en-US', {
        timeZone: timezone,
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
      });
    } catch {
      return '';
    }
  };

  return (
    <div className={`relative ${className}`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/[0.04] border border-white/[0.08] text-sm hover:bg-white/[0.08] transition-colors"
      >
        <Globe className="h-4 w-4 text-muted-foreground" />
        <span className="text-foreground">{selectedTimezone.label}</span>
        <span className="text-xs text-muted-foreground">
          {formatTimeInTimezone(selected)}
        </span>
        <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      <AnimatePresence>
        {isOpen && (
          <>
            {/* Backdrop */}
            <div
              className="fixed inset-0 z-40"
              onClick={() => setIsOpen(false)}
            />

            {/* Dropdown */}
            <motion.div
              initial={{ opacity: 0, y: -8, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -8, scale: 0.95 }}
              transition={{ duration: 0.15 }}
              className="absolute right-0 top-full mt-2 w-64 rounded-xl border border-white/[0.08] bg-[hsl(220,22%,12%)] shadow-xl z-50 overflow-hidden"
            >
              <div className="p-2 border-b border-white/[0.06]">
                <p className="text-xs text-muted-foreground px-2">
                  Select timezone for analytics display
                </p>
              </div>

              <div className="max-h-[300px] overflow-y-auto p-1">
                {TIMEZONES.map((tz) => (
                  <button
                    key={tz.value}
                    onClick={() => {
                      setSelected(tz.value);
                      setIsOpen(false);
                    }}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors ${
                      selected === tz.value
                        ? 'bg-amber-500/10 text-amber-400'
                        : 'text-foreground hover:bg-white/[0.06]'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-medium">{tz.label}</span>
                      <span className="text-xs text-muted-foreground">{tz.offset}</span>
                    </div>
                    {selected === tz.value && (
                      <Check className="h-4 w-4" />
                    )}
                  </button>
                ))}
              </div>

              <div className="p-2 border-t border-white/[0.06]">
                <p className="text-xs text-muted-foreground px-2">
                  Current time: {formatTimeInTimezone(selected)}
                </p>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

// Utility function to convert UTC timestamp to selected timezone
export function formatInTimezone(
  timestamp: string | Date,
  timezone: string = 'UTC',
  options?: Intl.DateTimeFormatOptions
): string {
  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp;
  
  const defaultOptions: Intl.DateTimeFormatOptions = {
    timeZone: timezone,
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  };
  
  return date.toLocaleString('en-US', { ...defaultOptions, ...options });
}

// Get the stored timezone preference
export function getStoredTimezone(): string {
  return localStorage.getItem(STORAGE_KEY) || 'UTC';
}

export default TimezoneSelector;
