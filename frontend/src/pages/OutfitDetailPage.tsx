import { useState } from "react";
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
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Heart,
  Bookmark,
  Share2,
  Eye,
  ChevronLeft,
  ShoppingBag,
  ExternalLink,
  MapPin,
  Calendar,
  Tag,
  Sparkles,
  Check,
} from "lucide-react";

// Types
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

interface OutfitStats {
  view_count: number;
  save_count: number;
  share_count: number;
  like_count: number;
  purchase_count: number;
  total_commission: number;
}

interface OutfitResponse {
  id: string;
  influencer_id: string;
  title: string;
  description: string | null;
  image_url: string;
  thumbnail_url: string | null;
  items: OutfitItem[];
  occasion: string | null;
  season: string | null;
  style_tags: string[];
  budget_range: { min: number; max: number; currency: string } | null;
  commission_rate: number;
  stats: OutfitStats;
  status: string;
  visibility: string;
  is_featured: boolean;
  is_liked: boolean;
  is_saved: boolean;
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

// API functions
const fetchOutfit = async (outfitId: string): Promise<OutfitResponse> => {
  const res = await fetch(`/api/influencers/outfits/${outfitId}`);
  if (!res.ok) throw new Error("Failed to fetch outfit");
  return res.json();
};

const likeOutfit = async (outfitId: string) => {
  const res = await fetch(`/api/influencers/outfits/${outfitId}/like`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to like outfit");
  return res.json();
};

const saveOutfit = async (outfitId: string, collectionName?: string) => {
  const res = await fetch(`/api/influencers/outfits/${outfitId}/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ collection_name: collectionName || "Saved" }),
  });
  if (!res.ok) throw new Error("Failed to save outfit");
  return res.json();
};

// Helper functions
const formatNumber = (num: number): string => {
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
  return num.toString();
};

const formatPrice = (price: number | null): string => {
  if (price === null) return "Price on request";
  return `$${price.toFixed(2)}`;
};

// Components
const ProductItemCard = ({ item, onShop }: { item: OutfitItem; onShop: () => void }) => (
  <Card className="group hover:shadow-md transition-all duration-300">
    <CardContent className="p-0">
      <div className="flex">
        <div className="w-20 h-20 bg-muted shrink-0">
          {item.product_image_url ? (
            <img
              src={item.product_image_url}
              alt={item.product_name || "Product"}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <ShoppingBag className="h-6 w-6 text-muted-foreground" />
            </div>
          )}
        </div>
        <div className="flex-1 p-3 min-w-0">
          {item.brand && (
            <p className="text-xs text-muted-foreground truncate">{item.brand}</p>
          )}
          <Link href={item.product_id ? `/product/${item.product_id}` : "#"}>
            <h4 className="font-medium text-sm truncate hover:text-primary transition-colors">
              {item.product_name || "Unknown Product"}
            </h4>
          </Link>
          <p className="text-sm font-semibold text-primary mt-1">
            {formatPrice(item.product_price)}
          </p>
          {item.note && (
            <p className="text-xs text-muted-foreground mt-1 line-clamp-1 italic">
              "{item.note}"
            </p>
          )}
        </div>
        <div className="p-2 flex items-center">
          <Button
            size="sm"
            variant="default"
            className="shrink-0"
            onClick={onShop}
          >
            Shop
            <ExternalLink className="h-3 w-3 ml-1" />
          </Button>
        </div>
      </div>
    </CardContent>
  </Card>
);

// Main Component
export default function OutfitDetailPage() {
  const { outfitId } = useParams<{ outfitId: string }>();
  const queryClient = useQueryClient();
  const [selectedItem, setSelectedItem] = useState<OutfitItem | null>(null);

  const { data: outfit, isLoading, error } = useQuery({
    queryKey: ["outfit", outfitId],
    queryFn: () => fetchOutfit(outfitId!),
    enabled: !!outfitId,
  });

  const likeMutation = useMutation({
    mutationFn: () => likeOutfit(outfitId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["outfit", outfitId] });
    },
  });

  const saveMutation = useMutation({
    mutationFn: () => saveOutfit(outfitId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["outfit", outfitId] });
    },
  });

  const handleShare = async () => {
    const url = window.location.href;
    if (navigator.share) {
      await navigator.share({
        title: outfit?.title || "Outfit",
        url,
      });
    } else {
      await navigator.clipboard.writeText(url);
    }
  };

  const handleShopItem = (item: OutfitItem) => {
    // Track affiliate click and redirect
    if (item.affiliate_link_id) {
      window.open(`/go/${item.affiliate_link_id}`, "_blank");
    } else if (item.product_id) {
      window.open(`/product/${item.product_id}`, "_blank");
    }
  };

  // Calculate total price
  const totalPrice = outfit?.items.reduce((sum, item) => {
    return sum + (item.product_price || 0);
  }, 0) || 0;

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Skeleton className="h-8 w-32 mb-6" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <Skeleton className="aspect-[3/4] rounded-lg" />
          <div className="space-y-4">
            <Skeleton className="h-10 w-3/4" />
            <Skeleton className="h-6 w-1/2" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-2/3" />
            <div className="flex gap-2 mt-4">
              <Skeleton className="h-10 w-24" />
              <Skeleton className="h-10 w-24" />
              <Skeleton className="h-10 w-24" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !outfit) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Card className="max-w-md mx-auto">
          <CardHeader>
            <CardTitle>Outfit Not Found</CardTitle>
            <CardDescription>
              This outfit doesn't exist or is not available.
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

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        {/* Back Link */}
        <Link
          href={`/influencer/${outfit.influencer_id}`}
          className="inline-flex items-center text-sm text-muted-foreground hover:text-primary mb-6 transition-colors"
        >
          <ChevronLeft className="h-4 w-4 mr-1" />
          Back to Storefront
        </Link>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Image Section */}
          <div className="relative">
            <div className="aspect-[3/4] rounded-lg overflow-hidden bg-muted">
              <img
                src={outfit.image_url}
                alt={outfit.title}
                className="w-full h-full object-cover"
              />
            </div>

            {/* Featured Badge */}
            {outfit.is_featured && (
              <div className="absolute top-4 left-4">
                <Badge className="bg-gradient-to-r from-amber-400 to-orange-500 text-white border-0 shadow-lg">
                  <Sparkles className="h-3 w-3 mr-1" />
                  Featured
                </Badge>
              </div>
            )}

            {/* Quick Stats */}
            <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between">
              <div className="flex items-center gap-4 text-white text-sm bg-black/40 backdrop-blur-sm rounded-full px-4 py-2">
                <span className="flex items-center gap-1">
                  <Eye className="h-4 w-4" />
                  {formatNumber(outfit.stats.view_count)}
                </span>
                <span className="flex items-center gap-1">
                  <Heart className="h-4 w-4" />
                  {formatNumber(outfit.stats.like_count)}
                </span>
                <span className="flex items-center gap-1">
                  <Bookmark className="h-4 w-4" />
                  {formatNumber(outfit.stats.save_count)}
                </span>
              </div>
            </div>
          </div>

          {/* Details Section */}
          <div className="space-y-6">
            {/* Title & Description */}
            <div>
              <h1 className="text-3xl font-bold">{outfit.title}</h1>
              {outfit.description && (
                <p className="text-muted-foreground mt-2">{outfit.description}</p>
              )}
            </div>

            {/* Tags */}
            <div className="flex flex-wrap gap-2">
              {outfit.occasion && (
                <Badge variant="secondary">
                  <MapPin className="h-3 w-3 mr-1" />
                  {outfit.occasion}
                </Badge>
              )}
              {outfit.season && (
                <Badge variant="outline">
                  <Calendar className="h-3 w-3 mr-1" />
                  {outfit.season}
                </Badge>
              )}
              {outfit.style_tags.map((tag) => (
                <Badge key={tag} variant="outline">
                  <Tag className="h-3 w-3 mr-1" />
                  {tag}
                </Badge>
              ))}
            </div>

            {/* Action Buttons */}
            <div className="flex items-center gap-3">
              <Button
                variant={outfit.is_liked ? "default" : "outline"}
                size="lg"
                onClick={() => likeMutation.mutate()}
                disabled={likeMutation.isPending}
              >
                <Heart className={`h-5 w-5 mr-2 ${outfit.is_liked ? "fill-current" : ""}`} />
                {outfit.is_liked ? "Liked" : "Like"}
              </Button>
              <Button
                variant={outfit.is_saved ? "secondary" : "outline"}
                size="lg"
                onClick={() => saveMutation.mutate()}
                disabled={saveMutation.isPending}
              >
                <Bookmark className={`h-5 w-5 mr-2 ${outfit.is_saved ? "fill-current" : ""}`} />
                {outfit.is_saved ? "Saved" : "Save"}
              </Button>
              <Button variant="outline" size="lg" onClick={handleShare}>
                <Share2 className="h-5 w-5" />
              </Button>
            </div>

            <Separator />

            {/* Budget Info */}
            {outfit.budget_range && (
              <Card className="bg-muted/50">
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">Budget Range</p>
                      <p className="font-semibold">
                        {outfit.budget_range.currency} {outfit.budget_range.min} - {outfit.budget_range.max}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-muted-foreground">Total Value</p>
                      <p className="font-semibold text-lg">${totalPrice.toFixed(2)}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Items List */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold">
                  Shop the Look ({outfit.items.length} items)
                </h2>
                {outfit.items.length > 0 && (
                  <Button variant="default">
                    Shop All
                    <ShoppingBag className="h-4 w-4 ml-2" />
                  </Button>
                )}
              </div>

              {outfit.items.length === 0 ? (
                <Card>
                  <CardContent className="py-8 text-center">
                    <ShoppingBag className="h-10 w-10 mx-auto text-muted-foreground" />
                    <p className="text-muted-foreground mt-2">
                      No items in this outfit yet
                    </p>
                  </CardContent>
                </Card>
              ) : (
                <ScrollArea className="h-[400px] pr-4">
                  <div className="space-y-3">
                    {outfit.items.map((item, index) => (
                      <ProductItemCard
                        key={index}
                        item={item}
                        onShop={() => handleShopItem(item)}
                      />
                    ))}
                  </div>
                </ScrollArea>
              )}
            </div>

            {/* Commission Info */}
            <Card className="bg-gradient-to-r from-pink-50 to-purple-50 dark:from-pink-950/20 dark:to-purple-950/20 border-pink-200 dark:border-pink-800">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-full bg-pink-100 dark:bg-pink-900/30">
                    <Check className="h-5 w-5 text-pink-600" />
                  </div>
                  <div>
                    <p className="font-medium">Supports the Creator</p>
                    <p className="text-sm text-muted-foreground">
                      Purchases from this outfit earn the creator a commission
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Published Date */}
            {outfit.published_at && (
              <p className="text-sm text-muted-foreground">
                Published on{" "}
                {new Date(outfit.published_at).toLocaleDateString("en-US", {
                  month: "long",
                  day: "numeric",
                  year: "numeric",
                })}
              </p>
            )}
          </div>
        </div>

        {/* More Outfits Section */}
        <Separator className="my-12" />
        <div>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold">More from this Creator</h2>
            <Link href={`/influencer/${outfit.influencer_id}`}>
              <Button variant="outline">
                View Storefront
                <ChevronLeft className="h-4 w-4 ml-1 rotate-180" />
              </Button>
            </Link>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {[...Array(6)].map((_, i) => (
              <Card key={i} className="aspect-[3/4] bg-muted animate-pulse" />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
