import { Badge } from "@/components/ui/badge";
import Link from 'next/link';
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { ChevronRight, Sparkles, Users, Verified } from "lucide-react";
import { HoverRevealCard, TiltCard } from "@/components/experience/interactive";

export type InfluencerCardModel = {
  id: string;
  display_name: string;
  avatar_url: string | null;
  tier: string;
  niches: string[];
  followers_count: number;
  total_outfits: number;
  is_verified: boolean;
  is_featured: boolean;
};

type Props = {
  influencer: InfluencerCardModel;
  formatNumber: (v: number) => string;
  getTierBadgeVariant: (tier: string) => "default" | "secondary" | "outline";
};

export function InfluencerCard({ influencer, formatNumber, getTierBadgeVariant }: Props) {
  return (
    <Link href={`/influencer/${influencer.id}`}>
      <TiltCard>
        <HoverRevealCard
          className="cursor-pointer"
          reveal={
            <div className="rounded-2xl bg-gradient-to-t from-black/80 via-black/35 to-transparent p-4 flex items-end">
              <div className="w-full flex items-center justify-between text-white/90 text-xs">
                <span>{formatNumber(influencer.followers_count)} followers</span>
                <span>{influencer.total_outfits} looks</span>
              </div>
            </div>
          }
        >
          <div className="relative">
            <div className="aspect-square bg-gradient-to-br from-pink-100 via-purple-50 to-indigo-100 flex items-center justify-center">
              <Avatar className="h-24 w-24 ring-4 ring-white shadow-lg">
                <AvatarImage src={influencer.avatar_url || undefined} />
                <AvatarFallback className="text-2xl font-semibold bg-gradient-to-br from-pink-400 to-purple-500 text-white">
                  {influencer.display_name.charAt(0).toUpperCase()}
                </AvatarFallback>
              </Avatar>
            </div>
            {influencer.is_verified && (
              <div className="absolute top-2 right-2 bg-white rounded-full p-1 shadow">
                <Verified className="h-4 w-4 text-blue-500" />
              </div>
            )}
            {influencer.is_featured && (
              <div className="absolute top-2 left-2">
                <Badge variant="default" className="bg-gradient-to-r from-amber-400 to-orange-500 text-white border-0">
                  <Sparkles className="h-3 w-3 mr-1" />
                  Featured
                </Badge>
              </div>
            )}
          </div>
          <div className="p-4">
            <h3 className="font-semibold text-lg truncate">{influencer.display_name}</h3>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant={getTierBadgeVariant(influencer.tier)} className="text-xs capitalize">
                {influencer.tier.replace("_", " ")}
              </Badge>
              <span className="text-muted-foreground text-sm flex items-center gap-1">
                <Users className="h-3 w-3" />
                {formatNumber(influencer.followers_count)}
              </span>
            </div>
            <div className="flex flex-wrap gap-1 mt-3">
              {influencer.niches.slice(0, 3).map((niche) => (
                <Badge key={niche} variant="outline" className="text-xs">
                  {niche}
                </Badge>
              ))}
            </div>
            <div className="flex items-center justify-between mt-3 text-sm text-muted-foreground">
              <span>{influencer.total_outfits} outfits</span>
              <ChevronRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
            </div>
          </div>
        </HoverRevealCard>
      </TiltCard>
    </Link>
  );
}

