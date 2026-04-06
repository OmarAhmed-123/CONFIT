import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { motion } from 'framer-motion';
import { MainLayout } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useToast } from '@/hooks/use-toast';
import { apiUrl } from '@/lib/api';
import { getAuthToken } from '@/lib/auth';
import { Sparkles, Upload, Image as ImageIcon, Plus, Loader2, Camera } from 'lucide-react';
import { GlassCard, TiltCard } from '@/components/shared';
import { ScrollReveal } from '@/components/motion/ScrollReveal';

interface Twin {
  id: string;
  reference_images: string[];
  twin_image_url?: string;
  skin_undertone?: string;
  environment: string;
  status: string;
  meta: unknown;
  created_at: string;
  updated_at: string;
  garment_product_id?: string;
}

interface Render {
  id: string;
  twin_id: string;
  environment?: string;
  garment_product_id?: string;
  image_url: string;
  created_at: string;
}

interface Product {
  id: string;
  name: string;
  description: string;
  category: string;
  price: number;
  image_url: string;
  tags: string[];
}

export default function DigitalTwinPage() {
  const { toast } = useToast();
  const searchParams = useSearchParams();
  const productId = searchParams.get('product');

  const [personalPhoto, setPersonalPhoto] = useState<File | null>(null);
  const [personalPhotoUrl, setPersonalPhotoUrl] = useState<string>('');
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [photoUrls, setPhotoUrls] = useState<string[]>(['', '', '']);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [twins, setTwins] = useState<Twin[]>([]);
  const [selectedTwin, setSelectedTwin] = useState<Twin | null>(null);
  const [renders, setRenders] = useState<Render[]>([]);
  const [activeRenderId, setActiveRenderId] = useState<string | null>(null);
  const [envPrompt, setEnvPrompt] = useState('beach_sunset');
  const [isRendering, setIsRendering] = useState(false);

  useEffect(() => {
    if (productId) {
      fetchProduct(productId);
    }
  }, [productId]);

  useEffect(() => {
    const token = getAuthToken();
    if (!token) return;
    fetch(apiUrl('/api/digital-twin'), {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => (res.ok ? res.json() : []))
      .then((data: Twin[]) => {
        setTwins(data);
        if (data.length > 0) {
          setSelectedTwin(data[0]);
          fetchRenders(data[0].id);
        }
      })
      .catch(() => {});
  }, []);

  const fetchProduct = async (id: string) => {
    try {
      const response = await fetch(apiUrl(`/api/products/${id}`));
      if (response.ok) {
        const product = await response.json();
        setSelectedProduct(product);
      }
    } catch (error) {
      console.error('Failed to fetch product:', error);
    }
  };

  const updatePhotoUrl = (index: number, value: string) => {
    setPhotoUrls((prev) => {
      const next = [...prev];
      next[index] = value;
      return next;
    });
  };

  const canSubmit = photoUrls.filter((u) => u.trim().length > 0).length >= 3;

  const handleCreateTwin = async () => {
    if (!canSubmit) {
      toast({ title: 'Add at least 3 photos', description: 'Please provide 3–5 clear URLs to your photos.' });
      return;
    }
    const token = getAuthToken();
    if (!token) {
      toast({ title: 'Sign in required', description: 'Please log in to create a digital twin.', variant: 'destructive' });
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await fetch(apiUrl('/api/digital-twin'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ reference_images: photoUrls.filter((url) => url.trim()) }),
      });
      if (!response.ok) {
        throw new Error('Failed to create digital twin');
      }
      const twin: Twin = await response.json();
      setTwins((prev) => [twin, ...prev]);
      setSelectedTwin(twin);
      setRenders([]);
      toast({ title: 'Digital Twin created', description: 'Training will begin shortly.' });
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to create digital twin';
      toast({ title: 'Error', description: msg, variant: 'destructive' });
    } finally {
      setIsSubmitting(false);
    }
  };

  const fetchRenders = async (twinId: string) => {
    const token = getAuthToken();
    if (!token) return;
    try {
      const res = await fetch(apiUrl(`/api/digital-twin/${twinId}/renders`), {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) return;
      const data: Render[] = await res.json();
      setRenders(data);
      setActiveRenderId(data[0]?.id ?? null);
    } catch {
      // ignore
    }
  };

  const handleRender = async () => {
    if (!selectedTwin) return;
    const token = getAuthToken();
    if (!token) {
      toast({ title: 'Sign in required', description: 'Please log in first.', variant: 'destructive' });
      return;
    }
    setIsRendering(true);
    try {
      const res = await fetch(apiUrl(`/api/digital-twin/${selectedTwin.id}/renders`), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          environment: envPrompt,
        }),
      });
      if (!res.ok) throw new Error('Render failed');
      const render: Render = await res.json();
      setRenders((prev) => [render, ...prev]);
      setActiveRenderId(render.id);
      toast({ title: 'Render created', description: 'New look generated for your twin.' });
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to generate render';
      toast({ title: 'Error', description: msg, variant: 'destructive' });
    } finally {
      setIsRendering(false);
    }
  };

  const handlePersonalPhotoUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setPersonalPhoto(file);
      const url = URL.createObjectURL(file);
      setPersonalPhotoUrl(url);
    }
  };

  const handleTryOn = async () => {
    if (!personalPhoto || !selectedProduct) return;
    // For now, simulate try-on - in real app, send to backend
    toast({ title: 'Try-on initiated', description: 'Processing your virtual try-on...' });
    // TODO: Implement actual try-on API call
  };

  return (
    <MainLayout>
      <div className="container py-8">
        {selectedProduct ? (
          /* Try-On Mode */
          <div className="max-w-4xl mx-auto">
            <ScrollReveal className="text-center mb-8">
              <h1 className="text-3xl font-bold mb-2">Virtual Try-On</h1>
              <p className="text-muted-foreground">
                Upload your photo and see how {selectedProduct.name} looks on you!
              </p>
            </ScrollReveal>

            <div className="grid md:grid-cols-2 gap-8">
              {/* Product Preview */}
              <div className="space-y-4">
                <h2 className="text-lg font-semibold">Selected Item</h2>
                <GlassCard className="p-4">
                  <TiltCard className="aspect-square bg-muted rounded-lg overflow-hidden mb-4">
                    {selectedProduct.image_url ? (
                      <img
                        src={selectedProduct.image_url}
                        alt={selectedProduct.name}
                        className="w-full h-full object-cover"
                        loading="lazy"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-muted-foreground">
                        <ImageIcon className="w-12 h-12" />
                      </div>
                    )}
                  </TiltCard>
                  <h3 className="font-semibold">{selectedProduct.name}</h3>
                  <p className="text-sm text-muted-foreground mb-2">{selectedProduct.description}</p>
                  <p className="font-bold text-primary">${selectedProduct.price}</p>
                </GlassCard>
              </div>

              {/* Personal Photo Upload */}
              <div className="space-y-4">
                <h2 className="text-lg font-semibold">Your Photo</h2>
                <GlassCard className="p-4">
                  <div className="aspect-square bg-muted rounded-lg overflow-hidden mb-4 border-2 border-dashed border-border">
                    {personalPhotoUrl ? (
                      <img
                        src={personalPhotoUrl}
                        alt="Your photo"
                        className="w-full h-full object-cover"
                        loading="lazy"
                      />
                    ) : (
                      <div className="w-full h-full flex flex-col items-center justify-center text-muted-foreground">
                        <Camera className="w-12 h-12 mb-2" />
                        <p className="text-sm">Upload your photo</p>
                        <p className="text-xs">Full body photo works best</p>
                      </div>
                    )}
                  </div>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handlePersonalPhotoUpload}
                    className="hidden"
                    id="personal-photo"
                  />
                  <label htmlFor="personal-photo">
                    <Button variant="outline" className="w-full" asChild>
                      <span>
                        <Upload className="w-4 h-4 mr-2" />
                        {personalPhotoUrl ? 'Change Photo' : 'Upload Photo'}
                      </span>
                    </Button>
                  </label>
                </GlassCard>
                <Button
                  className="w-full"
                  onClick={handleTryOn}
                  disabled={!personalPhoto}
                >
                  <Sparkles className="w-4 h-4 mr-2" />
                  Try On Virtually
                </Button>
              </div>
            </div>
          </div>
        ) : (
          /* Original Digital Twin Creation */
          <div className="max-w-6xl mx-auto grid gap-8 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)] items-start">
          {/* Left: Creation / Editor */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="space-y-6"
          >
            <div className="flex items-center gap-2 mb-2">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/5 border border-primary/10 text-primary/80 text-xs font-medium">
                <Sparkles className="w-3 h-3" />
                <span>Digital Twin</span>
              </div>
            </div>
            <h1 className="heading-section mb-2">Your Cinematic Twin</h1>
            <p className="text-muted-foreground mb-4 max-w-xl">
              Upload 3–5 clear photos and CONFIT will create a high‑fidelity digital twin you can style in any
              environment.
            </p>

            <GlassCard className="p-6 space-y-4">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                1. Source Photos
              </h2>
              <p className="text-sm text-muted-foreground">
                Paste image URLs from your gallery or cloud storage. For best results, use full‑body photos in
                different poses and lighting.
              </p>
              <div className="space-y-3">
                {photoUrls.map((value, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center text-xs text-muted-foreground">
                      {idx + 1}
                    </div>
                    <Input
                      value={value}
                      onChange={(e) => updatePhotoUrl(idx, e.target.value)}
                      placeholder="https://..."
                      className="flex-1"
                    />
                  </div>
                ))}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setPhotoUrls((prev) => [...prev, ''])}
                  className="inline-flex items-center gap-2"
                >
                  <Plus className="h-3 w-3" />
                  Add another
                </Button>
              </div>

              <div className="flex items-center justify-between pt-4">
                <div className="text-xs text-muted-foreground">
                  Use between <span className="font-semibold text-foreground">3 and 5</span> high‑quality photos.
                </div>
                <Button
                  type="button"
                  variant="hero"
                  disabled={!canSubmit || isSubmitting}
                  onClick={handleCreateTwin}
                  className="inline-flex items-center gap-2"
                >
                  {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                  {isSubmitting ? 'Creating...' : 'Create Digital Twin'}
                </Button>
              </div>
            </GlassCard>

            <div className="bg-card border border-border rounded-xl p-6 space-y-4">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                2. Environment & Scene
              </h2>
              <p className="text-sm text-muted-foreground">
                Describe where you want to see yourself: <span className="italic">“beach_sunset”</span>,{' '}
                <span className="italic">“office_meeting”</span>, <span className="italic">“runway_show”</span>, etc.
              </p>
              <Input
                value={envPrompt}
                onChange={(e) => setEnvPrompt(e.target.value)}
                placeholder="beach_sunset"
              />
              <div className="flex justify-end">
                <Button
                  type="button"
                  variant="outline"
                  disabled={!selectedTwin || isRendering}
                  onClick={handleRender}
                  className="inline-flex items-center gap-2"
                >
                  {isRendering ? <Loader2 className="h-4 w-4 animate-spin" /> : <ImageIcon className="h-4 w-4" />}
                  {isRendering ? 'Rendering...' : 'Generate Look'}
                </Button>
              </div>
            </div>
          </motion.div>

          {/* Right: Twins & Renders Gallery */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="space-y-6"
          >
            <div className="bg-card border border-border rounded-xl p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                  Your Twins
                </h2>
              </div>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {twins.length === 0 && (
                  <p className="text-sm text-muted-foreground">
                    No twins yet. Create your first digital twin on the left.
                  </p>
                )}
                {twins.map((twin) => (
                  <button
                    key={twin.id}
                    type="button"
                    onClick={() => {
                      setSelectedTwin(twin);
                      fetchRenders(twin.id);
                    }}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-left text-sm transition-colors ${
                      selectedTwin?.id === twin.id ? 'bg-primary/10 text-primary' : 'hover:bg-muted text-foreground'
                    }`}
                  >
                    <span className="font-medium">{twin.id.replace('twin-', 'Twin ')}</span>
                    <span className="text-xs uppercase tracking-wide text-muted-foreground">
                      {twin.status}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            <GlassCard className="p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                  Renders
                </h2>
                {selectedTwin && (
                  <span className="text-xs text-muted-foreground">
                    {renders.length} scene{renders.length === 1 ? '' : 's'}
                  </span>
                )}
              </div>
              {renders.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  Generate a look to see your digital twin in a new environment.
                </p>
              ) : (
                <div className="grid grid-cols-2 gap-4">
                  {renders.map((r) => (
                    <motion.div
                      key={r.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      onClick={() => setActiveRenderId(r.id)}
                      role="button"
                      tabIndex={0}
                      className={`group rounded-lg overflow-hidden border bg-muted/40 cursor-pointer transition-colors ${
                        activeRenderId === r.id ? "border-accent/60 ring-1 ring-accent/30" : "border-border"
                      }`}
                    >
                      <div className="aspect-[3/4] overflow-hidden">
                        <img
                          src={r.image_url}
                          alt={r.environment || 'Digital twin render'}
                          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                        />
                      </div>
                      <div className="p-3 flex items-center justify-between text-xs">
                        <span className="font-medium">{r.environment || 'scene'}</span>
                        <span className="text-muted-foreground">
                          {new Date(r.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </GlassCard>
          </motion.div>
          </div>
        )}
      </div>
    </MainLayout>
  );
}

