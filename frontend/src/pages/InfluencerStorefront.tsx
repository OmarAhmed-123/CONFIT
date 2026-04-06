import { useState, useEffect } from "react";
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Heart,
  Bookmark,
  Share2,
  Users,
  MapPin,
  Calendar,
  Link as LinkIcon,
  Instagram,
  Youtube,
  Twitter,
  Verified,
  ChevronLeft,
  Grid3X3,
  LayoutList,
  ShoppingBag,
  Star,
  MessageCircle,
  Send,
} from "lucide-react";

// Types
interface SocialLinks {
  instagram?: string;
  tiktok?: string;
  youtube?: string;
  pinterest?: string;
  twitter?: string;
  facebook?: string;
  website?: string;
}

interface InfluencerStats {
  followers_count: number;
  following_count: number;
  total_outfits: number;
  total_views: number;
  total_engagement: number;
  total_earnings: number;
  pending_commissions: number;
  paid_commissions: number;
}

interface InfluencerProfile {
  id: string;
  user_id: string;
  display_name: string;
  bio: string | null;
  avatar_url: string | null;
  banner_url: string | null;
  website_url: string | null;
  social_links: SocialLinks;
  tier: string;
  status: string;
  niches: string[];
  style_tags: string[];
  stats: InfluencerStats;
  is_verified: boolean;
  is_featured: boolean;
  created_at: string;
  updated_at: string;
  is_following: boolean | null;
}

interface OutfitItem {
  product_id: string | null;
  product_name: string | null;
  product_image_url: string | null;
  product_price: number | null;
  brand: string | null;
  note: string | null;
  position: number | null;
  affiliate_link_id: string | null;
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

interface ProductRecommendation {
  id: string;
  influencer_id: string;
  influencer_name: string | null;
  influencer_avatar: string | null;
  product_id: string;
  product_name: string | null;
  product_image_url: string | null;
  product_price: number | null;
  review_text: string | null;
  rating: number | null;
  pros: string[];
  cons: string[];
  affiliate_link_id: string | null;
  helpful_count: number;
  view_count: number;
  is_featured: boolean;
  created_at: string;
}

interface StorefrontData {
  profile: InfluencerProfile;
  featured_outfits: Outfit[];
  total_outfits: number;
  recommendations: ProductRecommendation[];
}

// API fetchers
const fetchStorefront = async (influencerId: string): Promise<StorefrontData> => {
  const res = await fetch(`/api/influencers/${influencerId}/storefront`, {
    headers: {
      "Content-Type": "application/json",
    },
  });
  if (!res.ok) throw new Error("Failed to fetch storefront");
  return res.json();
};

const followInfluencer = async (influencerId: string) => {
  const res = await fetch("/api/influencers/follow", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ influencer_id: influencerId }),
  });
  if (!res.ok) throw new Error("Failed to follow");
  return res.json();
};

const unfollowInfluencer = async (influencerId: string) => {
  const res = await fetch(`/api/influencers/follow/${influencerId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to unfollow");
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

const getTierGradient = (tier: string) => {
  switch (tier) {
    case "top_creator":
      return "from-amber-400 via-orange-500 to-red-500";
    case "established":
      return "from-purple-400 via-pink-500 to-rose-500";
    case "rising":
      return "from-blue-400 via-indigo-500 to-purple-500";
    default:
      return "from-gray-400 via-slate-500 to-zinc-500";
  }
};

// Components
const OutfitGridCard = ({ outfit }: { outfit: Outfit }) => (
  <Link href={`/influencer/outfit/${outfit.id}`}>
    <Card className="group hover:shadow-lg transition-all duration-300 overflow-hidden">
      <CardContent className="p-0">
        <div className="relative aspect-[3/4]">
          <img
            src={outfit.thumbnail_url || "/placeholder-outfit.jpg"}
            alt={outfit.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
          
          {outfit.is_featured && (
            <div className="absolute top-2 right-2">
              <Badge className="bg-gradient-to-r from-amber-400 to-orange-500 text-white border-0 text-xs">
                Featured
              </Badge>
            </div>
          )}

          <div className="absolute bottom-0 left-0 right-0 p-3">
            <h3 className="text-white font-semibold line-clamp-1">{outfit.title}</h3>
            {outfit.occasion && (
              <Badge variant="secondary" className="mt-1 text-xs">
                {outfit.occasion}
              </Badge>
            )}
            <div className="flex items-center gap-3 mt-2 text-white/80 text-sm">
              <span className="flex items-center gap-1">
                <Heart className="h-3 w-3" />
                {formatNumber(outfit.like_count)}
              </span>
              <span className="flex items-center gap-1">
                <Bookmark className="h-3 w-3" />
                {formatNumber(outfit.save_count)}
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  </Link>
);

const RecommendationCard = ({ rec }: { rec: ProductRecommendation }) => (
  <Card className="group hover:shadow-lg transition-all duration-300">
    <CardContent className="p-0">
      <div className="flex">
        <Link href={`/product/${rec.product_id}`} className="shrink-0">
          <div className="w-24 h-24 bg-muted">
            <img
              src={rec.product_image_url || "/placeholder-product.jpg"}
              alt={rec.product_name || "Product"}
              className="w-full h-full object-cover"
            />
          </div>
        </Link>
        <div className="flex-1 p-3">
          <Link href={`/product/${rec.product_id}`}>
            <h4 className="font-medium text-sm line-clamp-1 hover:text-primary">
              {rec.product_name}
            </h4>
          </Link>
          {rec.product_price && (
            <p className="text-sm font-semibold text-primary mt-1">
              ${rec.product_price.toFixed(2)}
            </p>
          )}
          {rec.rating && (
            <div className="flex items-center gap-1 mt-1">
              {[...Array(5)].map((_, i) => (
                <Star
                  key={i}
                  className={`h-3 w-3 ${
                    i < rec.rating! ? "text-amber-400 fill-amber-400" : "text-muted"
                  }`}
                />
              ))}
            </div>
          )}
          {rec.review_text && (
            <p className="text-xs text-muted-foreground line-clamp-2 mt-2">
              "{rec.review_text}"
            </p>
          )}
        </div>
      </div>
    </CardContent>
  </Card>
);

// Main Page Component
export default function InfluencerStorefront() {
  const { influencerId } = useParams<{ influencerId: string }>();
  const queryClient = useQueryClient();
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");

  const { data: storefront, isLoading, error } = useQuery({
    queryKey: ["storefront", influencerId],
    queryFn: () => fetchStorefront(influencerId!),
    enabled: !!influencerId,
  });

  const followMutation = useMutation({
    mutationFn: () => followInfluencer(influencerId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["storefront", influencerId] });
    },
  });

  const unfollowMutation = useMutation({
    mutationFn: () => unfollowInfluencer(influencerId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["storefront", influencerId] });
    },
  });

  const handleFollowToggle = () => {
    if (storefront?.profile.is_following) {
      unfollowMutation.mutate();
    } else {
      followMutation.mutate();
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background">
        <Skeleton className="h-64 w-full" />
        <div className="container mx-auto px-4 py-8">
          <div className="flex gap-6">
            <Skeleton className="h-24 w-24 rounded-full -mt-16 ring-4 ring-background" />
            <div className="flex-1 pt-4">
              <Skeleton className="h-8 w-48" />
              <Skeleton className="h-4 w-32 mt-2" />
            </div>
          </div>
          <Skeleton className="h-4 w-full mt-8" />
          <Skeleton className="h-4 w-3/4 mt-2" />
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mt-8">
            {[...Array(8)].map((_, i) => (
              <Skeleton key={i} className="aspect-[3/4]" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error || !storefront) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle>Creator Not Found</CardTitle>
            <CardDescription>
              This creator profile doesn't exist or is not available.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild>
              <Link href="/influencers">
                <ChevronLeft className="h-4 w-4 mr-2" />
                Back to Marketplace
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const { profile, featured_outfits, total_outfits, recommendations } = storefront;

  return (
    <div className="min-h-screen bg-background">
      {/* Banner */}
      <div className={`relative h-48 md:h-64 bg-gradient-to-r ${getTierGradient(profile.tier)}`}>
        {profile.banner_url && (
          <img
            src={profile.banner_url}
            alt=""
            className="absolute inset-0 w-full h-full object-cover mix-blend-overlay opacity-30"
          />
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-background/80 to-transparent" />
      </div>

      {/* Profile Header */}
      <div className="container mx-auto px-4">
        <div className="relative flex flex-col md:flex-row gap-6 -mt-16 md:-mt-12">
          {/* Avatar */}
          <Avatar className="h-28 w-28 md:h-32 md:w-32 ring-4 ring-background shadow-xl">
            <AvatarImage src={profile.avatar_url || undefined} />
            <AvatarFallback className="text-3xl font-bold bg-gradient-to-br from-pink-400 to-purple-500 text-white">
              {profile.display_name.charAt(0).toUpperCase()}
            </AvatarFallback>
          </Avatar>

          {/* Info */}
          <div className="flex-1 pt-4 md:pt-8">
            <div className="flex flex-col md:flex-row md:items-center gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-2xl md:text-3xl font-bold">{profile.display_name}</h1>
                  {profile.is_verified && (
                    <Verified className="h-6 w-6 text-blue-500" />
                  )}
                </div>
                <div className="flex items-center gap-3 mt-2">
                  <Badge variant={getTierBadgeVariant(profile.tier)} className="capitalize">
                    {profile.tier.replace("_", " ")}
                  </Badge>
                  {profile.is_featured && (
                    <Badge variant="secondary">
                      <Star className="h-3 w-3 mr-1" />
                      Featured Creator
                    </Badge>
                  )}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 md:ml-auto">
                <Button
                  variant={profile.is_following ? "secondary" : "default"}
                  onClick={handleFollowToggle}
                  disabled={followMutation.isPending || unfollowMutation.isPending}
                >
                  {profile.is_following ? (
                    <>
                      <Users className="h-4 w-4 mr-2" />
                      Following
                    </>
                  ) : (
                    <>
                      <Users className="h-4 w-4 mr-2" />
                      Follow
                    </>
                  )}
                </Button>
                <Dialog>
                  <DialogTrigger asChild>
                    <Button variant="outline" size="icon">
                      <Share2 className="h-4 w-4" />
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Share this Creator</DialogTitle>
                      <DialogDescription>
                        Share {profile.display_name}'s storefront with your friends
                      </DialogDescription>
                    </DialogHeader>
                    <div className="flex gap-2 mt-4">
                      <Button className="flex-1" variant="outline">
                        <Send className="h-4 w-4 mr-2" />
                        Copy Link
                      </Button>
                    </div>
                  </DialogContent>
                </Dialog>
              </div>
            </div>

            {/* Stats */}
            <div className="flex items-center gap-6 mt-4 text-sm">
              <div className="flex items-center gap-1">
                <Users className="h-4 w-4 text-muted-foreground" />
                <span className="font-semibold">{formatNumber(profile.stats.followers_count)}</span>
                <span className="text-muted-foreground">followers</span>
              </div>
              <div className="flex items-center gap-1">
                <ShoppingBag className="h-4 w-4 text-muted-foreground" />
                <span className="font-semibold">{total_outfits}</span>
                <span className="text-muted-foreground">outfits</span>
              </div>
            </div>

            {/* Niches */}
            <div className="flex flex-wrap gap-2 mt-3">
              {profile.niches.map((niche) => (
                <Badge key={niche} variant="outline" className="text-xs">
                  {niche}
                </Badge>
              ))}
            </div>
          </div>
        </div>

        {/* Bio */}
        {profile.bio && (
          <p className="mt-6 text-muted-foreground max-w-2xl">{profile.bio}</p>
        )}

        {/* Social Links */}
        <div className="flex items-center gap-3 mt-4">
          {profile.social_links.instagram && (
            <a
              href={profile.social_links.instagram}
              target="_blank"
              rel="noopener noreferrer"
              title="Instagram"
              className="text-muted-foreground hover:text-primary transition-colors"
            >
              <Instagram className="h-5 w-5" />
            </a>
          )}
          {profile.social_links.youtube && (
            <a
              href={profile.social_links.youtube}
              target="_blank"
              rel="noopener noreferrer"
              title="YouTube"
              className="text-muted-foreground hover:text-primary transition-colors"
            >
              <Youtube className="h-5 w-5" />
            </a>
          )}
          {profile.social_links.twitter && (
            <a
              href={profile.social_links.twitter}
              target="_blank"
              rel="noopener noreferrer"
              title="Twitter"
              className="text-muted-foreground hover:text-primary transition-colors"
            >
              <Twitter className="h-5 w-5" />
            </a>
          )}
          {profile.website_url && (
            <a
              href={profile.website_url}
              target="_blank"
              rel="noopener noreferrer"
              title="Website"
              className="text-muted-foreground hover:text-primary transition-colors flex items-center gap-1 text-sm"
            >
              <LinkIcon className="h-4 w-4" />
              Website
            </a>
          )}
        </div>

        <Separator className="my-8" />

        {/* Content Tabs */}
        <Tabs defaultValue="outfits" className="w-full">
          <TabsList className="w-full justify-start">
            <TabsTrigger value="outfits">
              Outfits ({total_outfits})
            </TabsTrigger>
            <TabsTrigger value="recommendations">
              Picks ({recommendations.length})
            </TabsTrigger>
            <TabsTrigger value="about">About</TabsTrigger>
          </TabsList>

          {/* Outfits Tab */}
          <TabsContent value="outfits" className="mt-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">Curated Outfits</h2>
              <div className="flex items-center gap-2">
                <Button
                  variant={viewMode === "grid" ? "default" : "ghost"}
                  size="icon"
                  onClick={() => setViewMode("grid")}
                >
                  <Grid3X3 className="h-4 w-4" />
                </Button>
                <Button
                  variant={viewMode === "list" ? "default" : "ghost"}
                  size="icon"
                  onClick={() => setViewMode("list")}
                >
                  <LayoutList className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {featured_outfits.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <ShoppingBag className="h-12 w-12 mx-auto text-muted-foreground" />
                  <h3 className="mt-4 font-semibold">No outfits yet</h3>
                  <p className="text-muted-foreground mt-1">
                    This creator hasn't published any outfits yet.
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {featured_outfits.map((outfit) => (
                  <OutfitGridCard key={outfit.id} outfit={outfit} />
                ))}
              </div>
            )}
          </TabsContent>

          {/* Recommendations Tab */}
          <TabsContent value="recommendations" className="mt-6">
            <h2 className="text-xl font-semibold mb-4">Creator Picks</h2>
            
            {recommendations.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <Star className="h-12 w-12 mx-auto text-muted-foreground" />
                  <h3 className="mt-4 font-semibold">No recommendations yet</h3>
                  <p className="text-muted-foreground mt-1">
                    This creator hasn't shared any product picks yet.
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {recommendations.map((rec) => (
                  <RecommendationCard key={rec.id} rec={rec} />
                ))}
              </div>
            )}
          </TabsContent>

          {/* About Tab */}
          <TabsContent value="about" className="mt-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Style Profile</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Style Tags</p>
                      <div className="flex flex-wrap gap-2 mt-2">
                        {profile.style_tags.map((tag) => (
                          <Badge key={tag} variant="secondary">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Niches</p>
                      <div className="flex flex-wrap gap-2 mt-2">
                        {profile.niches.map((niche) => (
                          <Badge key={niche} variant="outline">
                            {niche}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Stats</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-3 rounded-lg bg-muted/50">
                      <p className="text-2xl font-bold">{formatNumber(profile.stats.followers_count)}</p>
                      <p className="text-sm text-muted-foreground">Followers</p>
                    </div>
                    <div className="p-3 rounded-lg bg-muted/50">
                      <p className="text-2xl font-bold">{total_outfits}</p>
                      <p className="text-sm text-muted-foreground">Outfits</p>
                    </div>
                    <div className="p-3 rounded-lg bg-muted/50">
                      <p className="text-2xl font-bold">{formatNumber(profile.stats.total_views)}</p>
                      <p className="text-sm text-muted-foreground">Views</p>
                    </div>
                    <div className="p-3 rounded-lg bg-muted/50">
                      <p className="text-2xl font-bold">{formatNumber(profile.stats.total_engagement)}</p>
                      <p className="text-sm text-muted-foreground">Engagement</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="md:col-span-2">
                <CardHeader>
                  <CardTitle className="text-lg">Bio</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-muted-foreground">
                    {profile.bio || "No bio provided yet."}
                  </p>
                  <div className="flex items-center gap-2 mt-4 text-sm text-muted-foreground">
                    <Calendar className="h-4 w-4" />
                    <span>
                      Joined {new Date(profile.created_at).toLocaleDateString("en-US", {
                        month: "long",
                        year: "numeric",
                      })}
                    </span>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
