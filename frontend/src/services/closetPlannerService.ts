/**
 * CONFIT Frontend - Closet Planner Service
 * API client for Smart Closet Planner
 */

import { api } from '@/lib/api';

// Types
export interface WeatherData {
  temp_high: number;
  temp_low: number;
  condition: string;
  precipitation: number;
  humidity: number;
  wind_speed: number;
  uv_index?: number;
  icon?: string;
}

export interface CalendarEvent {
  id: string;
  title: string;
  time?: string;
  end_time?: string;
  type?: string;
  location?: string;
  dress_code?: string;
  importance: number;
}

export interface OutfitItem {
  id: string;
  name: string;
  category: string;
  color?: string;
  image_url?: string;
  brand?: string;
  price?: number;
}

export interface AlternativeOutfit {
  outfit_data: Record<string, unknown>;
  reason?: string;
  score?: number;
}

export interface DailyOutfit {
  id: string;
  plan_id: string;
  plan_date: string;
  day_of_week: number;
  day_name: string;
  outfit: {
    title: string;
    occasion: string;
    items: OutfitItem[];
    total_price?: number;
  };
  items: OutfitItem[];
  weather?: WeatherData;
  events: CalendarEvent[];
  primary_occasion?: string;
  occasion_confidence: number;
  alternatives: AlternativeOutfit[];
  status: 'planned' | 'worn' | 'skipped' | 'modified';
  worn_at?: string;
  user_rating?: number;
  user_notes?: string;
  style_match_score?: number;
  weather_match_score?: number;
  occasion_match_score?: number;
  overall_score?: number;
  created_at: string;
  updated_at: string;
}

export interface ClosetPlan {
  id: string;
  user_id: string;
  week_start_date: string;
  week_end_date: string;
  plan_name?: string;
  is_active: boolean;
  is_template: boolean;
  generation_context: Record<string, unknown>;
  total_outfits: number;
  days_planned: number;
  daily_outfits: DailyOutfit[];
  created_at: string;
  updated_at: string;
}

export interface PlannerPreferences {
  planning_day: number;
  planning_time: string;
  auto_generate: boolean;
  location: Record<string, unknown>;
  temperature_unit: string;
  weather_sensitivity: Record<string, unknown>;
  calendar_providers: string[];
  prefer_favorite_items: boolean;
  avoid_recently_worn: boolean;
  recently_worn_days: number;
  max_item_frequency: number;
  occasion_priorities: Record<string, number>;
  notify_new_plan: boolean;
  notify_daily: boolean;
  notify_daily_time: string;
}

export interface OutfitSuggestion {
  outfit_data: Record<string, unknown>;
  items: OutfitItem[];
  occasion: string;
  confidence: number;
  style_match_score: number;
  weather_match_score: number;
  occasion_match_score: number;
  overall_score: number;
  reasoning?: string;
}

export interface WeeklyPlanSummary {
  plan_id: string;
  week_start: string;
  week_end: string;
  total_days: number;
  days_planned: number;
  days_worn: number;
  days_skipped: number;
  average_rating?: number;
  top_occasions: Array<{ occasion: string; count: number }>;
  weather_summary: Record<string, unknown>;
  style_diversity_score: number;
}

// API Functions

/**
 * Get current week's plan
 */
export async function getCurrentPlan(): Promise<ClosetPlan | null> {
  return api.get<ClosetPlan | null>('/planner/current');
}

/**
 * Get a specific plan
 */
export async function getPlan(planId: string): Promise<ClosetPlan> {
  return api.get<ClosetPlan>(`/planner/${planId}`);
}

/**
 * Generate a new weekly plan
 */
export async function generatePlan(options?: {
  week_start_date?: string;
  plan_name?: string;
  force_regenerate?: boolean;
}): Promise<ClosetPlan> {
  return api.post<ClosetPlan>('/planner', options || {});
}

/**
 * Get plan summary
 */
export async function getPlanSummary(planId: string): Promise<WeeklyPlanSummary> {
  return api.get<WeeklyPlanSummary>(`/planner/${planId}/summary`);
}

/**
 * Update daily outfit
 */
export async function updateDailyOutfit(
  dailyOutfitId: string,
  data: {
    outfit_data?: Record<string, unknown>;
    status?: 'planned' | 'worn' | 'skipped' | 'modified';
    user_rating?: number;
    user_notes?: string;
    primary_occasion?: string;
  }
): Promise<DailyOutfit> {
  return api.patch<DailyOutfit>(`/planner/daily/${dailyOutfitId}`, data);
}

/**
 * Record outfit as worn
 */
export async function recordOutfitWorn(
  dailyOutfitId: string,
  data?: {
    actual_outfit?: Record<string, unknown>;
    satisfaction?: number;
    notes?: string;
  }
): Promise<void> {
  return api.post(`/planner/daily/${dailyOutfitId}/worn`, data);
}

/**
 * Swap outfits between days
 */
export async function swapOutfits(
  planId: string,
  sourceDate: string,
  targetDate: string
): Promise<[DailyOutfit, DailyOutfit]> {
  return api.post<[DailyOutfit, DailyOutfit]>(`/planner/${planId}/swap`, {
    source_date: sourceDate,
    target_date: targetDate,
  });
}

/**
 * Get outfit suggestions for a specific day
 */
export async function getSuggestions(data: {
  date: string;
  occasion?: string;
  weather_override?: WeatherData;
  events_override?: CalendarEvent[];
  excluded_item_ids?: string[];
  preferred_item_ids?: string[];
}): Promise<OutfitSuggestion[]> {
  return api.post<OutfitSuggestion[]>('/planner/suggestions', data);
}

/**
 * Get planner preferences
 */
export async function getPreferences(): Promise<PlannerPreferences> {
  return api.get<PlannerPreferences>('/planner/preferences');
}

/**
 * Update planner preferences
 */
export async function updatePreferences(
  data: Partial<PlannerPreferences>
): Promise<PlannerPreferences> {
  return api.patch<PlannerPreferences>('/planner/preferences', data);
}

/**
 * Get weather forecast
 */
export async function getWeatherForecast(startDate?: string): Promise<{
  location: string;
  forecasts: WeatherData[];
  fetched_at: string;
  source: string;
}> {
  return api.get('/planner/weather', startDate ? { start_date: startDate } : undefined);
}

/**
 * Get calendar events
 */
export async function getCalendarEvents(
  startDate?: string,
  endDate?: string
): Promise<CalendarEvent[]> {
  const params: Record<string, string | undefined> = {};
  if (startDate) params.start_date = startDate;
  if (endDate) params.end_date = endDate;
  return api.get<CalendarEvent[]>('/planner/calendar/events', params);
}

/**
 * Add manual calendar event
 */
export async function addCalendarEvent(event: {
  title: string;
  event_date?: string;
  time?: string;
  end_time?: string;
  type?: string;
  location?: string;
  dress_code?: string;
  importance?: number;
}): Promise<CalendarEvent> {
  return api.post<CalendarEvent>('/planner/calendar/events', event);
}

/**
 * Delete calendar event
 */
export async function deleteCalendarEvent(eventId: string): Promise<void> {
  return api.delete(`/planner/calendar/events/${eventId}`);
}

/**
 * Sync calendar from external provider
 */
export async function syncCalendar(data: {
  provider: 'google' | 'apple' | 'outlook' | 'manual';
  start_date?: string;
  end_date?: string;
  force_refresh?: boolean;
}): Promise<CalendarEvent[]> {
  return api.post<CalendarEvent[]>('/planner/calendar/sync', data);
}

// Utility functions

/**
 * Get weather icon based on condition
 */
export function getWeatherIcon(condition: string): string {
  const icons: Record<string, string> = {
    sunny: '☀️',
    clear: '🌙',
    partly_cloudy: '⛅',
    cloudy: '☁️',
    overcast: '☁️',
    light_rain: '🌧️',
    rain: '🌧️',
    heavy_rain: '⛈️',
    thunderstorm: '⛈️',
    light_snow: '🌨️',
    snow: '❄️',
    heavy_snow: '❄️',
    fog: '🌫️',
    windy: '💨',
  };
  return icons[condition.toLowerCase()] || '🌡️';
}

/**
 * Get weather description
 */
export function getWeatherDescription(weather: WeatherData): string {
  const temp = `${Math.round(weather.temp_high)}°/${Math.round(weather.temp_low)}°`;
  const condition = weather.condition.replace('_', ' ');
  let desc = `${temp} ${condition}`;
  
  if (weather.precipitation > 0) {
    desc += ` • ${weather.precipitation}mm rain`;
  }
  
  return desc;
}

/**
 * Format time for display
 */
export function formatEventTime(time?: string): string {
  if (!time) return '';
  const [hours, minutes] = time.split(':');
  const h = parseInt(hours);
  const ampm = h >= 12 ? 'PM' : 'AM';
  const hour = h % 12 || 12;
  return `${hour}:${minutes} ${ampm}`;
}

/**
 * Get occasion display name
 */
export function getOccasionDisplayName(occasion: string): string {
  const names: Record<string, string> = {
    work: 'Work',
    formal: 'Formal',
    casual: 'Casual',
    date_night: 'Date Night',
    party: 'Party',
    athletic: 'Athletic',
    everyday: 'Everyday',
    special_event: 'Special Event',
  };
  return names[occasion] || occasion;
}

/**
 * Get status color
 */
export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    planned: 'bg-blue-500',
    worn: 'bg-green-500',
    skipped: 'bg-gray-400',
    modified: 'bg-orange-500',
  };
  return colors[status] || 'bg-gray-400';
}
