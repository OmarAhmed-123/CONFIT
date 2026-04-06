/**
 * CONFIT - Smart Closet Planner Page
 * Weekly outfit planning with weather and calendar integration
 */

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence, DragControls } from 'framer-motion';
import { 
  Calendar, 
  CloudSun, 
  RefreshCw, 
  Settings, 
  ChevronLeft, 
  ChevronRight,
  Sparkles,
  MapPin,
  Clock,
  Shirt,
  X,
  Check,
  Star,
  MoreVertical,
  Droplets,
  Wind,
  Thermometer,
} from 'lucide-react';
import { format, addDays, startOfWeek, isToday, isTomorrow, parseISO } from 'date-fns';

import {
  getCurrentPlan,
  generatePlan,
  updateDailyOutfit,
  swapOutfits,
  getWeatherForecast,
  getCalendarEvents,
  getPreferences,
  ClosetPlan,
  DailyOutfit,
  WeatherData,
  CalendarEvent,
  PlannerPreferences,
  getWeatherIcon,
  getWeatherDescription,
  formatEventTime,
  getOccasionDisplayName,
  getStatusColor,
} from '@/services/closetPlannerService';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';
import { createTransition } from '@/motion';

// ─────────────────────────────────────────────────────────────────────────────
// WEATHER INDICATOR COMPONENT
// ─────────────────────────────────────────────────────────────────────────────

interface WeatherIndicatorProps {
  weather: WeatherData;
  compact?: boolean;
}

const WeatherIndicator: React.FC<WeatherIndicatorProps> = ({ weather, compact = false }) => {
  const icon = getWeatherIcon(weather.condition);
  
  if (compact) {
    return (
      <div className="flex items-center gap-1.5 text-sm">
        <span className="text-lg">{icon}</span>
        <span className="font-medium">{Math.round(weather.temp_high)}°</span>
      </div>
    );
  }
  
  return (
    <motion.div 
      className="bg-gradient-to-br from-blue-50 to-sky-100 dark:from-blue-950 dark:to-sky-900 rounded-xl p-4"
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={createTransition({ duration: 0.3 })}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <motion.span 
            className="text-4xl"
            animate={{ scale: [1, 1.1, 1] }}
            transition={createTransition({ duration: 2, repeat: Infinity })}
          >
            {icon}
          </motion.span>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold">{Math.round(weather.temp_high)}°</span>
              <span className="text-muted-foreground">/ {Math.round(weather.temp_low)}°</span>
            </div>
            <p className="text-sm text-muted-foreground capitalize">
              {weather.condition.replace('_', ' ')}
            </p>
          </div>
        </div>
        
        <div className="flex flex-col gap-1 text-xs text-muted-foreground">
          {weather.precipitation > 0 && (
            <div className="flex items-center gap-1">
              <Droplets className="h-3 w-3" />
              <span>{weather.precipitation}mm</span>
            </div>
          )}
          {weather.humidity > 0 && (
            <div className="flex items-center gap-1">
              <Wind className="h-3 w-3" />
              <span>{Math.round(weather.humidity)}%</span>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// OUTFIT CARD COMPONENT
// ─────────────────────────────────────────────────────────────────────────────

interface OutfitCardProps {
  dailyOutfit: DailyOutfit;
  onSwap?: (date: string) => void;
  onEdit?: () => void;
  onMarkWorn?: () => void;
  isDragging?: boolean;
  dragControls?: DragControls;
}

const OutfitCard: React.FC<OutfitCardProps> = ({
  dailyOutfit,
  onSwap,
  onEdit,
  onMarkWorn,
  isDragging,
  dragControls,
}) => {
  const { outfit, weather, events, items, status, overall_score } = dailyOutfit;
  
  const isPastOrToday = new Date(dailyOutfit.plan_date) <= new Date();
  
  return (
    <motion.div
      className={cn(
        "relative bg-card rounded-xl border-2 transition-all duration-300",
        isDragging && "shadow-2xl scale-105 border-primary",
        status === 'worn' && "opacity-75",
        status === 'skipped' && "opacity-50"
      )}
      drag={!!onSwap}
      dragControls={dragControls}
      dragListeners={false}
      whileDrag={{ scale: 1.05, zIndex: 50 }}
      whileHover={{ scale: 1.02 }}
      layout
    >
      {/* Status Badge */}
      <div className="absolute -top-2 -right-2 z-10">
        <Badge className={cn("text-xs", getStatusColor(status))}>
          {status}
        </Badge>
      </div>
      
      {/* Score Badge */}
      {overall_score && (
        <div className="absolute -top-2 -left-2 z-10">
          <Badge variant="secondary" className="text-xs">
            {Math.round(overall_score * 100)}% match
          </Badge>
        </div>
      )}
      
      <div className="p-4 space-y-3">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h3 className="font-semibold text-lg">{outfit.title}</h3>
            <p className="text-sm text-muted-foreground">
              {getOccasionDisplayName(outfit.occasion)}
            </p>
          </div>
          
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={onEdit}>
                <Shirt className="mr-2 h-4 w-4" />
                Edit Outfit
              </DropdownMenuItem>
              {onSwap && (
                <DropdownMenuItem onClick={() => onSwap(dailyOutfit.plan_date)}>
                  <Calendar className="mr-2 h-4 w-4" />
                  Swap with Another Day
                </DropdownMenuItem>
              )}
              {isPastOrToday && status === 'planned' && onMarkWorn && (
                <DropdownMenuItem onClick={onMarkWorn}>
                  <Check className="mr-2 h-4 w-4" />
                  Mark as Worn
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        
        {/* Weather */}
        {weather && (
          <div className="mt-2">
            <WeatherIndicator weather={weather} compact />
          </div>
        )}
        
        {/* Events */}
        {events.length > 0 && (
          <div className="space-y-1">
            {events.slice(0, 2).map((event, idx) => (
              <div key={idx} className="flex items-center gap-2 text-xs text-muted-foreground">
                <Clock className="h-3 w-3" />
                <span className="truncate">{event.title}</span>
                {event.time && <span className="ml-auto">{formatEventTime(event.time)}</span>}
              </div>
            ))}
            {events.length > 2 && (
              <p className="text-xs text-muted-foreground">+{events.length - 2} more events</p>
            )}
          </div>
        )}
        
        {/* Outfit Items Preview */}
        <div className="flex flex-wrap gap-2 mt-3">
          {items.slice(0, 4).map((item, idx) => (
            <motion.div
              key={item.id}
              className="relative group"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={createTransition({ delay: idx * 0.05 })}
            >
              <div className="w-14 h-14 rounded-lg bg-muted overflow-hidden">
                {item.image_url ? (
                  <img 
                    src={item.image_url} 
                    alt={item.name}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <Shirt className="h-6 w-6 text-muted-foreground" />
                  </div>
                )}
              </div>
              <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity rounded-lg flex items-center justify-center">
                <span className="text-white text-xs text-center px-1 truncate">{item.name}</span>
              </div>
            </motion.div>
          ))}
          {items.length > 4 && (
            <div className="w-14 h-14 rounded-lg bg-muted flex items-center justify-center">
              <span className="text-sm text-muted-foreground">+{items.length - 4}</span>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// DAY COLUMN COMPONENT
// ─────────────────────────────────────────────────────────────────────────────

interface DayColumnProps {
  dailyOutfit?: DailyOutfit;
  date: Date;
  onDrop?: (sourceDate: string) => void;
  onSwap?: (date: string) => void;
  onEdit?: () => void;
  onMarkWorn?: () => void;
  isDropTarget?: boolean;
}

const DayColumn: React.FC<DayColumnProps> = ({
  dailyOutfit,
  date,
  onDrop,
  onSwap,
  onEdit,
  onMarkWorn,
  isDropTarget,
}) => {
  const dayName = format(date, 'EEE');
  const dayNum = format(date, 'd');
  const isTodayDate = isToday(date);
  const isTomorrowDate = isTomorrow(date);
  
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };
  
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const sourceDate = e.dataTransfer.getData('text/plain');
    if (onDrop && sourceDate) {
      onDrop(sourceDate);
    }
  };
  
  return (
    <div
      className={cn(
        "flex flex-col min-h-[300px] rounded-xl transition-all duration-200",
        isDropTarget && "bg-primary/10 ring-2 ring-primary ring-dashed",
        isTodayDate && "bg-primary/5"
      )}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {/* Day Header */}
      <div className={cn(
        "text-center py-3 border-b",
        isTodayDate && "bg-primary text-primary-foreground rounded-t-xl"
      )}>
        <p className="text-xs font-medium opacity-75">{dayName}</p>
        <p className="text-xl font-bold">{dayNum}</p>
        {isTodayDate && <Badge variant="secondary" className="mt-1 text-xs">Today</Badge>}
        {isTomorrowDate && <Badge variant="outline" className="mt-1 text-xs">Tomorrow</Badge>}
      </div>
      
      {/* Outfit Card or Empty State */}
      <div className="flex-1 p-3">
        {dailyOutfit ? (
          <OutfitCard
            dailyOutfit={dailyOutfit}
            onSwap={onSwap}
            onEdit={onEdit}
            onMarkWorn={onMarkWorn}
          />
        ) : (
          <div className="h-full flex items-center justify-center">
            <div className="text-center text-muted-foreground">
              <Shirt className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No outfit planned</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// MAIN CLOSET PLANNER PAGE
// ─────────────────────────────────────────────────────────────────────────────

const ClosetPlannerPage: React.FC = () => {
  const { toast } = useToast();
  
  const [plan, setPlan] = useState<ClosetPlan | null>(null);
  const [preferences, setPreferences] = useState<PlannerPreferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [currentWeekStart, setCurrentWeekStart] = useState(() => 
    startOfWeek(new Date(), { weekStartsOn: 0 })
  );
  const [dragSource, setDragSource] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  
  // Fetch current plan
  const fetchPlan = useCallback(async () => {
    try {
      setLoading(true);
      const [planData, prefsData] = await Promise.all([
        getCurrentPlan(),
        getPreferences(),
      ]);
      setPlan(planData);
      setPreferences(prefsData);
    } catch (error) {
      console.error('Failed to fetch plan:', error);
      toast({
        title: 'Error',
        description: 'Failed to load closet plan',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);
  
  useEffect(() => {
    fetchPlan();
  }, [fetchPlan]);
  
  // Generate new plan
  const handleGeneratePlan = async () => {
    try {
      setGenerating(true);
      const newPlan = await generatePlan({
        week_start_date: format(currentWeekStart, 'yyyy-MM-dd'),
        force_regenerate: true,
      });
      setPlan(newPlan);
      toast({
        title: 'Plan Generated! ✨',
        description: 'Your weekly outfit plan is ready',
      });
    } catch (error) {
      console.error('Failed to generate plan:', error);
      toast({
        title: 'Error',
        description: 'Failed to generate outfit plan',
        variant: 'destructive',
      });
    } finally {
      setGenerating(false);
    }
  };
  
  // Swap outfits
  const handleSwap = async (sourceDate: string, targetDate: string) => {
    if (!plan) return;
    
    try {
      const [source, target] = await swapOutfits(plan.id, sourceDate, targetDate);
      
      // Update local state
      setPlan(prev => {
        if (!prev) return prev;
        return {
          ...prev,
          daily_outfits: prev.daily_outfits.map(d => {
            if (d.plan_date === sourceDate) return { ...d, ...source };
            if (d.plan_date === targetDate) return { ...d, ...target };
            return d;
          }),
        };
      });
      
      toast({
        title: 'Outfits Swapped',
        description: 'Your outfit schedule has been updated',
      });
    } catch (error) {
      console.error('Failed to swap outfits:', error);
      toast({
        title: 'Error',
        description: 'Failed to swap outfits',
        variant: 'destructive',
      });
    }
  };
  
  // Mark as worn
  const handleMarkWorn = async (dailyOutfitId: string) => {
    try {
      await updateDailyOutfit(dailyOutfitId, { status: 'worn' });
      
      setPlan(prev => {
        if (!prev) return prev;
        return {
          ...prev,
          daily_outfits: prev.daily_outfits.map(d =>
            d.id === dailyOutfitId ? { ...d, status: 'worn' } : d
          ),
        };
      });
      
      toast({
        title: 'Outfit Marked as Worn',
        description: 'Your wardrobe analytics will be updated',
      });
    } catch (error) {
      console.error('Failed to mark as worn:', error);
      toast({
        title: 'Error',
        description: 'Failed to update outfit status',
        variant: 'destructive',
      });
    }
  };
  
  // Navigate weeks
  const goToPreviousWeek = () => {
    setCurrentWeekStart(prev => addDays(prev, -7));
  };
  
  const goToNextWeek = () => {
    setCurrentWeekStart(prev => addDays(prev, 7));
  };
  
  // Get outfit for a specific date
  const getOutfitForDate = (date: Date): DailyOutfit | undefined => {
    const dateStr = format(date, 'yyyy-MM-dd');
    return plan?.daily_outfits.find(d => d.plan_date === dateStr);
  };
  
  // Generate days for the week
  const weekDays = Array.from({ length: 7 }, (_, i) => addDays(currentWeekStart, i));
  
  return (
    <div className="container mx-auto px-4 py-6 max-w-7xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Sparkles className="h-8 w-8 text-primary" />
            Smart Closet Planner
          </h1>
          <p className="text-muted-foreground mt-1">
            AI-powered weekly outfit planning
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="icon"
            onClick={() => setShowSettings(true)}
          >
            <Settings className="h-4 w-4" />
          </Button>
          
          <Button
            onClick={handleGeneratePlan}
            disabled={generating}
            className="gap-2"
          >
            {generating ? (
              <RefreshCw className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            {generating ? 'Generating...' : 'Generate Plan'}
          </Button>
        </div>
      </div>
      
      {/* Week Navigation */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={goToPreviousWeek}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <div className="text-lg font-semibold min-w-[200px] text-center">
            {format(currentWeekStart, 'MMM d')} - {format(addDays(currentWeekStart, 6), 'MMM d, yyyy')}
          </div>
          <Button variant="outline" size="icon" onClick={goToNextWeek}>
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
        
        {preferences?.location && (
          <div className="flex items-center gap-2 text-muted-foreground">
            <MapPin className="h-4 w-4" />
            <span className="text-sm">
              {preferences.location.city as string || 'Location not set'}
            </span>
          </div>
        )}
      </div>
      
      {/* Loading State */}
      {loading && (
        <div className="grid grid-cols-7 gap-4">
          {weekDays.map((_, i) => (
            <Card key={i} className="min-h-[300px]">
              <CardContent className="p-4">
                <Skeleton className="h-full w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      )}
      
      {/* Weekly Calendar Grid */}
      {!loading && (
        <motion.div 
          className="grid grid-cols-7 gap-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={createTransition({ duration: 0.3 })}
        >
          {weekDays.map((day, idx) => (
            <motion.div
              key={day.toISOString()}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={createTransition({ delay: idx * 0.05 })}
            >
              <DayColumn
                date={day}
                dailyOutfit={getOutfitForDate(day)}
                onDrop={(sourceDate) => handleSwap(sourceDate, format(day, 'yyyy-MM-dd'))}
                onSwap={(date) => setDragSource(date)}
                onMarkWorn={() => {
                  const outfit = getOutfitForDate(day);
                  if (outfit) handleMarkWorn(outfit.id);
                }}
                isDropTarget={dragSource !== null}
              />
            </motion.div>
          ))}
        </motion.div>
      )}
      
      {/* Empty State */}
      {!loading && !plan && (
        <div className="text-center py-16">
          <Shirt className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
          <h2 className="text-xl font-semibold mb-2">No Plan Yet</h2>
          <p className="text-muted-foreground mb-6">
            Generate your first weekly outfit plan
          </p>
          <Button onClick={handleGeneratePlan} disabled={generating} size="lg">
            <Sparkles className="mr-2 h-5 w-5" />
            Generate My Plan
          </Button>
        </div>
      )}
      
      {/* Plan Summary */}
      {plan && (
        <motion.div 
          className="mt-8 grid grid-cols-4 gap-4"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={createTransition({ delay: 0.3 })}
        >
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold">{plan.days_planned}</p>
              <p className="text-sm text-muted-foreground">Days Planned</p>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold">
                {plan.daily_outfits.filter(d => d.status === 'worn').length}
              </p>
              <p className="text-sm text-muted-foreground">Outfits Worn</p>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold">
                {Math.round(
                  plan.daily_outfits.reduce((acc, d) => acc + (d.overall_score || 0), 0) / 
                  plan.daily_outfits.length * 100
                )}%
              </p>
              <p className="text-sm text-muted-foreground">Avg Match Score</p>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-2xl font-bold capitalize">
                {plan.daily_outfits[0]?.primary_occasion || 'Mixed'}
              </p>
              <p className="text-sm text-muted-foreground">Top Occasion</p>
            </CardContent>
          </Card>
        </motion.div>
      )}
    </div>
  );
};

export default ClosetPlannerPage;
