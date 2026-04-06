import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import Link from 'next/link';
import { Badge } from "@/components/ui/badge";
import { Bookmark, Heart, Sparkles } from "lucide-react";
import { InteractiveCard } from "@/components/experience/interactive";

export type OutfitPreviewModel = {
  id: string;
  influencer_name: string | null;
  influencer_avatar: string | null;
  title: string;
  thumbnail_url: string | null;
  occasion: string | null;
  like_count: number;
  save_count: number;
  is_featured: boolean;
};

type Props = {
  outfit: OutfitPreviewModel;
  formatNumber: (v: number) => string;
};

export function OutfitPreview({ outfit, formatNumber }: Props) {
  return (
    <Link href={`/influencer/outfit/${outfit.id}`}>
      <InteractiveCard>
        <div className="relative aspect-[3/4]">
          <img
            src={outfit.thumbnail_url || "/placeholder-outfit.jpg"}
            alt={outfit.title}
            loading="lazy"
            className="w-full h-full object-cover blur-[0.5px] group-hover:scale-105 group-hover:blur-0 transition-all duration-300"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />

          <div className="absolute top-3 left-3 flex items-center gap-2">
            <Avatar className="h-8 w-8 ring-2 ring-white">
              <AvatarImage src={outfit.influencer_avatar || undefined} />
              <AvatarFallback className="text-xs">{outfit.influencer_name?.charAt(0)}</AvatarFallback>
            </Avatar>
            <span className="text-white text-sm font-medium drop-shadow">{outfit.influencer_name}</span>
          </div>

          {outfit.is_featured && (
            <div className="absolute top-3 right-3">
              <Badge className="bg-gradient-to-r from-amber-400 to-orange-500 text-white border-0">
                <Sparkles className="h-3 w-3 mr-1" />
                Featured
              </Badge>
            </div>
          )}

          <div className="absolute bottom-0 left-0 right-0 p-3">
            <h3 className="text-white font-semibold text-lg line-clamp-1">{outfit.title}</h3>
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
      </InteractiveCard>
    </Link>
  );
}

