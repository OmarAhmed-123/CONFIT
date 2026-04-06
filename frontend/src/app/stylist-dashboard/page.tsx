/**
 * Stylist Dashboard Page
 * Dashboard for professional stylists to manage clients and create outfits
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import {
    Users, Palette, Calendar, DollarSign, TrendingUp, Star, Briefcase,
    MessageSquare, Eye, Clock, Award, ShoppingBag, Heart, Sparkles
} from 'lucide-react';
import { MainLayout } from '@/components/layout/MainLayout';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAuth } from '@/context/AuthContext';
import { AppRole, useRBAC } from '@/hooks/useRBAC';
import { cn } from '@/lib/utils';

// Mock stylist data
const MOCK_CLIENTS = [
    { id: '1', name: 'Sarah Johnson', avatar: '', lastSession: '2 hours ago', upcomingAppointment: 'Tomorrow 3PM', stylePreference: 'Minimalist', totalSessions: 12 },
    { id: '2', name: 'Michael Chen', avatar: '', lastSession: '1 day ago', upcomingAppointment: 'Friday 5PM', stylePreference: 'Business Casual', totalSessions: 8 },
    { id: '3', name: 'Emma Williams', avatar: '', lastSession: '3 days ago', upcomingAppointment: null, stylePreference: 'Bohemian', totalSessions: 5 },
    { id: '4', name: 'David Kim', avatar: '', lastSession: '1 week ago', upcomingAppointment: 'Next Monday', stylePreference: 'Streetwear', totalSessions: 3 },
];

const MOCK_OUTFITS = [
    { id: '1', name: 'Summer Wedding Guest', client: 'Sarah Johnson', items: 5, likes: 24, views: 156, created: '2 days ago' },
    { id: '2', name: 'Office Refresh Collection', client: 'Michael Chen', items: 8, likes: 18, views: 89, created: '4 days ago' },
    { id: '3', name: 'Weekend Getaway Looks', client: 'Emma Williams', items: 4, likes: 32, views: 201, created: '1 week ago' },
];

const STATS = [
    { label: 'Active Clients', value: '24', icon: Users, trend: '+3 this month', color: 'text-blue-500' },
    { label: 'Outfits Created', value: '156', icon: Palette, trend: '+12 this week', color: 'text-pink-500' },
    { label: 'Upcoming Sessions', value: '8', icon: Calendar, trend: 'Next: Tomorrow 3PM', color: 'text-purple-500' },
    { label: 'Total Earnings', value: '$4,250', icon: DollarSign, trend: '+$850 this month', color: 'text-green-500' },
];

export default function StylistDashboardPage() {
    const router = useRouter();
    const { user, isAuthenticated, isLoading: authLoading } = useAuth();
    const rbac = useRBAC();
    const [activeTab, setActiveTab] = useState('overview');
    const canAccessDashboard = rbac.hasAnyRole([AppRole.ADMIN, AppRole.STYLIST]);

    useEffect(() => {
        if (!authLoading && !isAuthenticated) {
            router.push('/login?redirect=/stylist-dashboard');
            return;
        }

        if (!authLoading && isAuthenticated && !canAccessDashboard) {
            router.replace('/?error=unauthorized');
        }
    }, [authLoading, canAccessDashboard, isAuthenticated, router]);

    if (authLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-spin h-8 w-8 border-4 border-pink-500 border-t-transparent rounded-full" />
            </div>
        );
    }

    if (!isAuthenticated || !canAccessDashboard) {
        return null;
    }

    return (
        <MainLayout>
            <div className="container mx-auto px-4 py-8 max-w-7xl">
                {/* Header */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-8"
                >
                    <div className="flex items-center gap-4 mb-2">
                        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-pink-500 to-purple-500 flex items-center justify-center">
                            <Sparkles className="h-6 w-6 text-white" />
                        </div>
                        <div>
                            <h1 className="text-3xl font-display font-semibold">Stylist Dashboard</h1>
                            <p className="text-muted-foreground">Welcome back, {user?.name || 'Stylist'}!</p>
                        </div>
                    </div>
                </motion.div>

                {/* Stats Grid */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                    className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8"
                >
                    {STATS.map((stat, i) => {
                        const Icon = stat.icon;
                        return (
                            <Card key={i} className="hover:shadow-lg transition-shadow">
                                <CardContent className="p-6">
                                    <div className="flex items-center justify-between mb-2">
                                        <Icon className={cn('h-5 w-5', stat.color)} />
                                        <TrendingUp className="h-4 w-4 text-green-500" />
                                    </div>
                                    <div className="text-2xl font-bold">{stat.value}</div>
                                    <div className="text-sm text-muted-foreground">{stat.label}</div>
                                    <div className="text-xs text-green-600 mt-1">{stat.trend}</div>
                                </CardContent>
                            </Card>
                        );
                    })}
                </motion.div>

                {/* Main Content */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                >
                    <Tabs value={activeTab} onValueChange={setActiveTab}>
                        <TabsList className="mb-6">
                            <TabsTrigger value="overview">Overview</TabsTrigger>
                            <TabsTrigger value="clients">Clients</TabsTrigger>
                            <TabsTrigger value="outfits">My Outfits</TabsTrigger>
                            <TabsTrigger value="schedule">Schedule</TabsTrigger>
                        </TabsList>

                        <TabsContent value="overview" className="space-y-6">
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                                {/* Recent Clients */}
                                <Card>
                                    <CardHeader>
                                        <CardTitle className="flex items-center gap-2">
                                            <Users className="h-5 w-5 text-pink-500" />
                                            Recent Clients
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="space-y-4">
                                            {MOCK_CLIENTS.slice(0, 3).map((client) => (
                                                <div key={client.id} className="flex items-center gap-3 p-3 rounded-lg hover:bg-muted/50 transition-colors cursor-pointer">
                                                    <Avatar>
                                                        <AvatarImage src={client.avatar} />
                                                        <AvatarFallback>{client.name.split(' ').map(n => n[0]).join('')}</AvatarFallback>
                                                    </Avatar>
                                                    <div className="flex-1 min-w-0">
                                                        <div className="font-medium truncate">{client.name}</div>
                                                        <div className="text-sm text-muted-foreground">{client.stylePreference}</div>
                                                    </div>
                                                    <div className="text-xs text-muted-foreground">{client.lastSession}</div>
                                                </div>
                                            ))}
                                        </div>
                                        <Button variant="outline" className="w-full mt-4" onClick={() => setActiveTab('clients')}>
                                            View All Clients
                                        </Button>
                                    </CardContent>
                                </Card>

                                {/* Recent Outfits */}
                                <Card>
                                    <CardHeader>
                                        <CardTitle className="flex items-center gap-2">
                                            <Palette className="h-5 w-5 text-purple-500" />
                                            Recent Outfits
                                        </CardTitle>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="space-y-4">
                                            {MOCK_OUTFITS.map((outfit) => (
                                                <div key={outfit.id} className="flex items-center gap-3 p-3 rounded-lg hover:bg-muted/50 transition-colors cursor-pointer">
                                                    <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-pink-500/20 to-purple-500/20 flex items-center justify-center">
                                                        <Palette className="h-5 w-5 text-pink-500" />
                                                    </div>
                                                    <div className="flex-1 min-w-0">
                                                        <div className="font-medium truncate">{outfit.name}</div>
                                                        <div className="text-sm text-muted-foreground">for {outfit.client}</div>
                                                    </div>
                                                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                                                        <span className="flex items-center gap-1">
                                                            <Heart className="h-3 w-3" /> {outfit.likes}
                                                        </span>
                                                        <span className="flex items-center gap-1">
                                                            <Eye className="h-3 w-3" /> {outfit.views}
                                                        </span>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                        <Button variant="outline" className="w-full mt-4" onClick={() => setActiveTab('outfits')}>
                                            View All Outfits
                                        </Button>
                                    </CardContent>
                                </Card>
                            </div>

                            {/* Quick Actions */}
                            <Card>
                                <CardHeader>
                                    <CardTitle>Quick Actions</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                                        <Button variant="outline" className="h-auto py-4 flex-col gap-2">
                                            <Palette className="h-5 w-5 text-pink-500" />
                                            <span>Create Outfit</span>
                                        </Button>
                                        <Button variant="outline" className="h-auto py-4 flex-col gap-2">
                                            <Users className="h-5 w-5 text-blue-500" />
                                            <span>Add Client</span>
                                        </Button>
                                        <Button variant="outline" className="h-auto py-4 flex-col gap-2">
                                            <Calendar className="h-5 w-5 text-purple-500" />
                                            <span>Schedule Session</span>
                                        </Button>
                                        <Button variant="outline" className="h-auto py-4 flex-col gap-2">
                                            <MessageSquare className="h-5 w-5 text-green-500" />
                                            <span>Messages</span>
                                        </Button>
                                    </div>
                                </CardContent>
                            </Card>
                        </TabsContent>

                        <TabsContent value="clients">
                            <Card>
                                <CardHeader>
                                    <div className="flex items-center justify-between">
                                        <CardTitle>All Clients</CardTitle>
                                        <Button>
                                            <Users className="h-4 w-4 mr-2" />
                                            Add New Client
                                        </Button>
                                    </div>
                                </CardHeader>
                                <CardContent>
                                    <div className="space-y-4">
                                        {MOCK_CLIENTS.map((client) => (
                                            <div key={client.id} className="flex items-center gap-4 p-4 rounded-lg border hover:shadow-md transition-all cursor-pointer">
                                                <Avatar className="h-12 w-12">
                                                    <AvatarImage src={client.avatar} />
                                                    <AvatarFallback>{client.name.split(' ').map(n => n[0]).join('')}</AvatarFallback>
                                                </Avatar>
                                                <div className="flex-1 min-w-0">
                                                    <div className="font-medium">{client.name}</div>
                                                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                                        <Badge variant="secondary">{client.stylePreference}</Badge>
                                                        <span>·</span>
                                                        <span>{client.totalSessions} sessions</span>
                                                    </div>
                                                </div>
                                                <div className="text-right">
                                                    {client.upcomingAppointment ? (
                                                        <div className="text-sm">
                                                            <div className="text-muted-foreground">Next session</div>
                                                            <div className="font-medium text-pink-600">{client.upcomingAppointment}</div>
                                                        </div>
                                                    ) : (
                                                        <div className="text-sm text-muted-foreground">No upcoming</div>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </CardContent>
                            </Card>
                        </TabsContent>

                        <TabsContent value="outfits">
                            <Card>
                                <CardHeader>
                                    <div className="flex items-center justify-between">
                                        <CardTitle>My Outfit Creations</CardTitle>
                                        <Button>
                                            <Palette className="h-4 w-4 mr-2" />
                                            Create New Outfit
                                        </Button>
                                    </div>
                                </CardHeader>
                                <CardContent>
                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                        {MOCK_OUTFITS.map((outfit) => (
                                            <div key={outfit.id} className="p-4 rounded-lg border hover:shadow-lg transition-all cursor-pointer group">
                                                <div className="aspect-video rounded-lg bg-gradient-to-br from-pink-500/10 to-purple-500/10 flex items-center justify-center mb-3 group-hover:from-pink-500/20 group-hover:to-purple-500/20 transition-colors">
                                                    <Palette className="h-8 w-8 text-pink-500" />
                                                </div>
                                                <div className="font-medium mb-1">{outfit.name}</div>
                                                <div className="text-sm text-muted-foreground mb-2">for {outfit.client}</div>
                                                <div className="flex items-center justify-between text-xs text-muted-foreground">
                                                    <span>{outfit.items} items</span>
                                                    <div className="flex items-center gap-3">
                                                        <span className="flex items-center gap-1">
                                                            <Heart className="h-3 w-3" /> {outfit.likes}
                                                        </span>
                                                        <span className="flex items-center gap-1">
                                                            <Eye className="h-3 w-3" /> {outfit.views}
                                                        </span>
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </CardContent>
                            </Card>
                        </TabsContent>

                        <TabsContent value="schedule">
                            <Card>
                                <CardHeader>
                                    <CardTitle>Upcoming Sessions</CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="text-center py-12">
                                        <Calendar className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                                        <h3 className="font-medium mb-2">No sessions scheduled</h3>
                                        <p className="text-sm text-muted-foreground mb-4">Start by scheduling a session with a client</p>
                                        <Button>
                                            <Calendar className="h-4 w-4 mr-2" />
                                            Schedule Session
                                        </Button>
                                    </div>
                                </CardContent>
                            </Card>
                        </TabsContent>
                    </Tabs>
                </motion.div>
            </div>
        </MainLayout>
    );
}
