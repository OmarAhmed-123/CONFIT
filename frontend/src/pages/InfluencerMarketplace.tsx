import { useState, useEffect } from "react";
import Link from 'next/link';
import { useQuery } from "@tanstack/react-query";
import { MainLayout } from "@/components/layout";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import {
  Carousel,
  CarouselContent,
  CarouselItem,
  CarouselNext,
  CarouselPrevious,
} from "@/components/ui/carousel";
import {
  Heart,
  Bookmark,
  Share2,
  Users,
  TrendingUp,
  Star,
  Verified,
  Search,
  Sparkles,
  ChevronRight,
  MapPin,
  DollarSign,
} from "lucide-react";
import { AnimatedSection, HoverRevealCard, InteractiveCard, ScrollReveal, TiltCard } from "@/components/experience/interactive";
import {
  InfluencerCard as SharedInfluencerCard,
  OutfitPreview as SharedOutfitPreview,
} from "@/components/shared";

// Types
interface Influencer {
  id: string;
  display_name: string;
  avatar_url: string | null;
  tier: string;
  niches: string[];
  followers_count: number;
  total_outfits: number;
  is_verified: boolean;
  is_featured: boolean;
}

interface Outfit {
  id: string;
  influencer_id: string;
  influencer_name: string | null;
  influencer_avatar: string | null;
  title: string;
  thumbnail_url: string | null;
  occasion: string | null;
  style_tags: string[];
  like_count: number;
  save_count: number;
  is_featured: boolean;
  published_at: string | null;
}

interface Category {
  id: string;
  name: string;
  icon: string;
}

// API fetchers
const fetchDiscover = async () => {
  const res = await fetch("/api/influencers/discover");
  if (!res.ok) throw new Error("Failed to fetch discover data");
  return res.json();
};

const fetchInfluencers = async (params: { tier?: string; niche?: string; search?: string }) => {
  const searchParams = new URLSearchParams();
  if (params.tier) searchParams.append("tier", params.tier);
  if (params.niche) searchParams.append("niche", params.niche);
  if (params.search) searchParams.append("search", params.search);
  const res = await fetch(`/api/influencers?${searchParams.toString()}`);
  if (!res.ok) throw new Error("Failed to fetch influencers");
  return res.json();
};

const fetchOutfitFeed = async (page: number = 1) => {
  const res = await fetch(`/api/influencers/feed/outfits?page=${page}&page_size=20`);
  if (!res.ok) throw new Error("Failed to fetch outfit feed");
  return res.json();
};

// Helper functions
const formatNumber = (num: number): string => {
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
  return num.toString();
};

const getTierBadgeVariant = (tier: string) => {
  switch (tier) {
    case "top_creator":
      return "default";
    case "established":
      return "secondary";
    case "rising":
      return "outline";
    default:
      return "outline";
  }
};

// Components
const InfluencerCard = ({ influencer }: { influencer: Influencer }) => (
  <SharedInfluencerCard
    influencer={influencer}
    formatNumber={formatNumber}
    getTierBadgeVariant={getTierBadgeVariant}
  />
);

const OutfitCard = ({ outfit }: { outfit: Outfit }) => (
  <SharedOutfitPreview outfit={outfit} formatNumber={formatNumber} />
);

const CategoryPill = ({ category, onClick }: { category: Category; onClick: () => void }) => (
  <Button
    variant="outline"
    className="rounded-full px-4 py-2 h-auto"
    onClick={onClick}
  >
    <span className="mr-2">{category.icon}</span>
    {category.name}
  </Button>
);

// Main Page Component
export default function InfluencerMarketplace() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [feedPage, setFeedPage] = useState(1);

  const { data: discoverData, isLoading: discoverLoading } = useQuery({
    queryKey: ["influencer-discover"],
    queryFn: fetchDiscover,
  });

  const { data: influencersData, isLoading: influencersLoading } = useQuery({
    queryKey: ["influencers", searchQuery, selectedCategory],
    queryFn: () => fetchInfluencers({ search: searchQuery, niche: selectedCategory || undefined }),
    enabled: !!searchQuery || !!selectedCategory,
  });

  const { data: feedData, isLoading: feedLoading } = useQuery({
    queryKey: ["outfit-feed", feedPage],
    queryFn: () => fetchOutfitFeed(feedPage),
  });

  const categories: Category[] = discoverData?.categories || [];

  return (
    <MainLayout>
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
      {/* Hero Section */}
      <ScrollReveal className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-pink-500/10 via-purple-500/10 to-indigo-500/10" />
        <div className="container mx-auto px-4 py-12 relative">
          <div className="text-center max-w-3xl mx-auto">
            <Badge variant="secondary" className="mb-4">
              <Sparkles className="h-3 w-3 mr-1" />
              Creator Marketplace
            </Badge>
            <h1 className="text-4xl md:text-5xl font-bold mb-4 bg-gradient-to-r from-pink-600 via-purple-600 to-indigo-600 bg-clip-text text-transparent">
              Discover Style Inspiration
            </h1>
            <p className="text-lg text-muted-foreground mb-8">
              Shop curated outfits from top fashion creators. Every purchase supports your favorite influencers.
            </p>

            {/* Search Bar */}
            <div className="relative max-w-xl mx-auto">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
              <Input
                placeholder="Search creators, styles, or occasions..."
                className="pl-10 pr-4 py-6 text-lg rounded-full shadow-lg"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </div>

          {/* Categories */}
          <div className="flex flex-wrap justify-center gap-3 mt-8">
            {categories.map((category: Category) => (
              <CategoryPill
                key={category.id}
                category={category}
                onClick={() => setSelectedCategory(selectedCategory === category.id ? null : category.id)}
              />
            ))}
          </div>
        </div>
      </ScrollReveal>

      {/* Featured Outfits Carousel */}
      {!discoverLoading && discoverData?.featured_outfits?.length > 0 && (
        <AnimatedSection className="container mx-auto px-4 py-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-2xl font-bold">Featured Outfits</h2>
              <p className="text-muted-foreground">Hand-picked looks from top creators</p>
            </div>
            <Button variant="ghost" asChild>
              <Link href="/influencers/outfits">
                View all <ChevronRight className="h-4 w-4 ml-1" />
              </Link>
            </Button>
          </div>
          <Carousel
            opts={{
              align: "start",
              loop: true,
            }}
            className="w-full"
          >
            <CarouselContent className="-ml-4">
              {discoverData.featured_outfits.map((outfit: Outfit) => (
                <CarouselItem key={outfit.id} className="pl-4 md:basis-1/2 lg:basis-1/3 xl:basis-1/4">
                  <OutfitCard outfit={outfit} />
                </CarouselItem>
              ))}
            </CarouselContent>
            <CarouselPrevious className="left-0" />
            <CarouselNext className="right-0" />
          </Carousel>
        </AnimatedSection>
      )}

      {/* Main Content Tabs */}
      <AnimatedSection className="container mx-auto px-4 py-8">
        <Tabs defaultValue="outfits" className="w-full">
          <TabsList className="grid w-full max-w-md mx-auto grid-cols-3 mb-8">
            <TabsTrigger value="outfits">Outfits</TabsTrigger>
            <TabsTrigger value="creators">Creators</TabsTrigger>
            <TabsTrigger value="trending">Trending</TabsTrigger>
          </TabsList>

          {/* Outfits Tab */}
          <TabsContent value="outfits">
            {feedLoading ? (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {[...Array(8)].map((_, i) => (
                  <Card key={i} className="overflow-hidden">
                    <div className="aspect-[3/4] bg-muted animate-pulse" />
                  </Card>
                ))}
              </div>
            ) : (
              <>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {feedData?.outfits?.map((outfit: Outfit) => (
                    <OutfitCard key={outfit.id} outfit={outfit} />
                  ))}
                </div>
                {feedData?.has_more && (
                  <div className="flex justify-center mt-8">
                    <Button
                      variant="outline"
                      size="lg"
                      onClick={() => setFeedPage((p) => p + 1)}
                    >
                      Load More
                    </Button>
                  </div>
                )}
              </>
            )}
          </TabsContent>

          {/* Creators Tab */}
          <TabsContent value="creators">
            {influencersLoading ? (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                {[...Array(10)].map((_, i) => (
                  <Card key={i} className="overflow-hidden">
                    <div className="aspect-square bg-muted animate-pulse" />
                  </Card>
                ))}
              </div>
            ) : influencersData ? (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                {influencersData.map((influencer: Influencer) => (
                  <InfluencerCard key={influencer.id} influencer={influencer} />
                ))}
              </div>
            ) : (
              discoverData?.trending_influencers && (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                  {discoverData.trending_influencers.map((influencer: Influencer) => (
                    <InfluencerCard key={influencer.id} influencer={influencer} />
                  ))}
                </div>
              )
            )}
          </TabsContent>

          {/* Trending Tab */}
          <TabsContent value="trending">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Top Creators */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="h-5 w-5 text-pink-500" />
                    Top Creators
                  </CardTitle>
                  <CardDescription>Most followed style influencers</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {discoverData?.trending_influencers?.slice(0, 5).map((influencer: Influencer, index: number) => (
                      <Link
                        key={influencer.id}
                        href={`/influencer/${influencer.id}`}
                        className="flex items-center gap-4 p-2 rounded-lg hover:bg-muted transition-colors"
                      >
                        <span className="text-lg font-bold text-muted-foreground w-6">{index + 1}</span>
                        <Avatar className="h-10 w-10">
                          <AvatarImage src={influencer.avatar_url || undefined} />
                          <AvatarFallback>{influencer.display_name.charAt(0)}</AvatarFallback>
                        </Avatar>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium truncate flex items-center gap-1">
                            {influencer.display_name}
                            {influencer.is_verified && <Verified className="h-4 w-4 text-blue-500" />}
                          </p>
                          <p className="text-sm text-muted-foreground">
                            {formatNumber(influencer.followers_count)} followers
                          </p>
                        </div>
                        <Badge variant={getTierBadgeVariant(influencer.tier)} className="capitalize">
                          {influencer.tier.replace("_", " ")}
                        </Badge>
                      </Link>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Quick Stats */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Star className="h-5 w-5 text-amber-500" />
                    Platform Stats
                  </CardTitle>
                  <CardDescription>Community highlights</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 rounded-lg bg-gradient-to-br from-pink-50 to-purple-50 dark:from-pink-950/20 dark:to-purple-950/20">
                      <p className="text-3xl font-bold text-pink-600">1.2K+</p>
                      <p className="text-sm text-muted-foreground">Active Creators</p>
                    </div>
                    <div className="p-4 rounded-lg bg-gradient-to-br from-purple-50 to-indigo-50 dark:from-purple-950/20 dark:to-indigo-950/20">
                      <p className="text-3xl font-bold text-purple-600">50K+</p>
                      <p className="text-sm text-muted-foreground">Curated Outfits</p>
                    </div>
                    <div className="p-4 rounded-lg bg-gradient-to-br from-indigo-50 to-blue-50 dark:from-indigo-950/20 dark:to-blue-950/20">
                      <p className="text-3xl font-bold text-indigo-600">$2M+</p>
                      <p className="text-sm text-muted-foreground">Creator Earnings</p>
                    </div>
                    <div className="p-4 rounded-lg bg-gradient-to-br from-amber-50 to-orange-50 dark:from-amber-950/20 dark:to-orange-950/20">
                      <p className="text-3xl font-bold text-amber-600">500K+</p>
                      <p className="text-sm text-muted-foreground">Happy Shoppers</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </AnimatedSection>

      {/* Become a Creator CTA */}
      <ScrollReveal className="container mx-auto px-4 py-12">
        <Card className="overflow-hidden">
          <div className="md:flex">
            <div className="md:w-1/2 bg-gradient-to-br from-pink-500 via-purple-500 to-indigo-500 p-8 md:p-12 text-white">
              <h2 className="text-3xl font-bold mb-4">Become a Creator</h2>
              <p className="text-white/90 mb-6">
                Share your style, curate outfits, and earn commissions on every purchase. Join our community of fashion creators.
              </p>
              <ul className="space-y-3 mb-6">
                <li className="flex items-center gap-2">
                  <DollarSign className="h-5 w-5" />
                  <span>Earn up to 15% commission on sales</span>
                </li>
                <li className="flex items-center gap-2">
                  <Users className="h-5 w-5" />
                  <span>Build your following and influence</span>
                </li>
                <li className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5" />
                  <span>Track your performance with analytics</span>
                </li>
              </ul>
              <Button size="lg" variant="secondary" className="bg-white text-purple-600 hover:bg-white/90" asChild>
                <Link href="/influencer/apply">
                  Apply Now
                  <ChevronRight className="h-4 w-4 ml-1" />
                </Link>
              </Button>
            </div>
            <div className="md:w-1/2 p-8 md:p-12 bg-muted/30">
              <h3 className="font-semibold mb-4">Creator Benefits</h3>
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-pink-100 dark:bg-pink-900/20">
                    <Sparkles className="h-4 w-4 text-pink-600" />
                  </div>
                  <div>
                    <p className="font-medium">Custom Storefront</p>
                    <p className="text-sm text-muted-foreground">Create your personalized shop with curated collections</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/20">
                    <TrendingUp className="h-4 w-4 text-purple-600" />
                  </div>
                  <div>
                    <p className="font-medium">Analytics Dashboard</p>
                    <p className="text-sm text-muted-foreground">Track clicks, conversions, and earnings in real-time</p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-indigo-100 dark:bg-indigo-900/20">
                    <Star className="h-4 w-4 text-indigo-600" />
                  </div>
                  <div>
                    <p className="font-medium">Featured Placement</p>
                    <p className="text-sm text-muted-foreground">Top creators get featured on our homepage</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Card>
      </ScrollReveal>
    </div>
    </MainLayout>
  );
}
