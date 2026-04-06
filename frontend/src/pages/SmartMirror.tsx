import { useCallback, useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { MainLayout } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { apiUrl } from '@/lib/api';
import { getAuthToken } from '@/lib/auth';
import { useToast } from '@/hooks/use-toast';
import { Camera, QrCode, MapPin, CheckCircle2 } from 'lucide-react';

type ScanResult = { id: string; product_sku: string; store_id?: string; product_data: any; scanned_at: string };

export default function SmartMirrorPage() {
  const { toast } = useToast();
  const token = getAuthToken();

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [cameraOn, setCameraOn] = useState(false);
  const [qr, setQr] = useState('');
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [route, setRoute] = useState<{ store_id: string; route: { product_id: string; aisle: number; shelf: string }[] } | null>(null);

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setCameraOn(false);
  }, []);

  const start = useCallback(async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      toast({ title: 'Camera not supported', description: 'Use manual QR input instead.' });
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      setCameraOn(true);
    } catch {
      toast({ title: 'Camera blocked', description: 'Please allow camera access or use manual input.', variant: 'destructive' });
    }
  }, [toast]);

  useEffect(() => {
    return () => stop();
  }, [stop]);

  const handleScan = useCallback(async (code: string) => {
    if (!token) {
      toast({ title: 'Sign in required', description: 'Please log in to use Smart Mirror.', variant: 'destructive' });
      return;
    }
    try {
      const res = await fetch(apiUrl('/api/omni/qr-scan'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ product_sku: code }),
      });
      if (!res.ok) throw new Error('Scan failed');
      const data = await res.json();
      setScanResult(data);
      toast({ title: 'QR scanned', description: `Product ${data.product_sku} scanned.` });
    } catch {
      toast({ title: 'Scan failed', description: 'Please try again.', variant: 'destructive' });
    }
  }, [token, toast]);

  const handleRoute = useCallback(async () => {
    if (!token) return;
    if (!scanResult?.product_sku) return;
    const storeId = scanResult.store_id || 'store-demo';
    try {
      const res = await fetch(apiUrl(`/api/omni/store-route?store_id=${encodeURIComponent(storeId)}&product_ids=${encodeURIComponent(scanResult.product_sku)}`), {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('route failed');
      const data = await res.json();
      setRoute(data);
    } catch {
      toast({ title: 'Route unavailable', description: 'Unable to generate store route.' });
    }
  }, [token, scanResult, toast]);

  return (
    <MainLayout>
      <div className="container py-8">
        <div className="max-w-6xl mx-auto grid gap-8 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
          <motion.div initial={{ opacity: 0, x: -16 }} animate={{ opacity: 1, x: 0 }} className="space-y-6">
            <div>
              <div className="inline-flex items-center gap-2 bg-accent/10 text-accent px-4 py-2 rounded-full mb-3">
                <QrCode className="h-4 w-4" />
                <span className="text-sm font-medium">Smart Mirror</span>
              </div>
              <h1 className="heading-section">In‑Store Try‑On Bridge</h1>
              <p className="text-muted-foreground">
                Scan a garment QR code in‑store to instantly bring it into your CONFIT experience.
              </p>
            </div>

            <div className="bg-card border border-border rounded-xl p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold">Scan QR</h2>
                <div className="flex gap-2">
                  {!cameraOn ? (
                    <Button variant="outline" onClick={start} className="gap-2">
                      <Camera className="h-4 w-4" />
                      Open camera
                    </Button>
                  ) : (
                    <Button variant="outline" onClick={stop}>
                      Close camera
                    </Button>
                  )}
                </div>
              </div>

              {cameraOn && (
                <div className="rounded-xl overflow-hidden border border-border bg-muted">
                  <video ref={videoRef} autoPlay playsInline className="w-full aspect-video object-cover" />
                  <div className="p-3 text-xs text-muted-foreground">
                    Camera scanning is browser‑dependent. If it doesn’t work on your device, use manual input below.
                  </div>
                </div>
              )}

              <div className="flex gap-2">
                <Input value={qr} onChange={(e) => setQr(e.target.value)} placeholder="Enter QR code text" />
                <Button variant="hero" onClick={() => handleScan(qr)} disabled={!qr.trim()} className="gap-2">
                  <CheckCircle2 className="h-4 w-4" />
                  Scan
                </Button>
              </div>
            </div>

            {scanResult?.product_sku && (
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="bg-card border border-border rounded-xl p-6 space-y-4">
                <h2 className="font-semibold">Result</h2>
                <div className="text-sm text-muted-foreground">
                  Scanned product: <span className="font-medium text-foreground">{scanResult.product_sku}</span>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" onClick={handleRoute} className="gap-2">
                    <MapPin className="h-4 w-4" />
                    In‑store route
                  </Button>
                  <Button variant="hero" asChild>
                    <a href="/digital-twin">Try with Digital Twin</a>
                  </Button>
                </div>
              </motion.div>
            )}
          </motion.div>

          <motion.aside initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }} className="space-y-6">
            <div className="bg-card border border-border rounded-xl p-6 space-y-3">
              <h2 className="font-semibold">Store Route</h2>
              {!route ? (
                <p className="text-sm text-muted-foreground">Generate a route after scanning a product.</p>
              ) : (
                <div className="space-y-3">
                  {route.route.map((r) => (
                    <div key={r.product_id} className="flex items-center justify-between p-3 rounded-lg bg-muted/40">
                      <span className="text-sm font-medium">{r.product_id}</span>
                      <span className="text-xs text-muted-foreground">Aisle {r.aisle} • Shelf {r.shelf}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.aside>
        </div>
      </div>
    </MainLayout>
  );
}

