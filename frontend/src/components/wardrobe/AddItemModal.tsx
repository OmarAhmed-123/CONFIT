import { useState, useRef, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    X,
    Upload,
    Camera,
    Image,
    Check,
    ChevronDown,
    MessageCircle,
    Sparkles
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { ProductCategory } from '@/types';

interface AddItemModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (item: WardrobeItemInput) => void;
}

export interface WardrobeItemInput {
    name: string;
    category: ProductCategory;
    color: string;
    brand: string;
    image: string;
    tags: string[];
}

const categories: { value: ProductCategory; label: string }[] = [
    { value: 'tops', label: 'Tops' },
    { value: 'bottoms', label: 'Bottoms' },
    { value: 'dresses', label: 'Dresses' },
    { value: 'outerwear', label: 'Outerwear' },
    { value: 'shoes', label: 'Shoes' },
    { value: 'accessories', label: 'Accessories' },
    { value: 'bags', label: 'Bags' },
];

const colors = [
    { name: 'Black', hex: '#0D0D0D' },
    { name: 'White', hex: '#FAFAFA' },
    { name: 'Navy', hex: '#1E3A5F' },
    { name: 'Red', hex: '#C41E3A' },
    { name: 'Blue', hex: '#4169E1' },
    { name: 'Green', hex: '#228B22' },
    { name: 'Brown', hex: '#8B4513' },
    { name: 'Beige', hex: '#F5F5DC' },
    { name: 'Gray', hex: '#808080' },
    { name: 'Pink', hex: '#FFB6C1' },
];

const popularBrands = [
    'Zara', 'H&M', 'Nike', 'Adidas', 'Uniqlo',
    'Gap', 'Levi\'s', 'Mango', 'Other'
];

export function AddItemModal({ isOpen, onClose, onSave }: AddItemModalProps) {
    const fileInputRef = useRef<HTMLInputElement>(null);
    const cameraInputRef = useRef<HTMLInputElement>(null);
    const videoRef = useRef<HTMLVideoElement>(null);
    const captureCanvasRef = useRef<HTMLCanvasElement>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const [imagePreview, setImagePreview] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [cameraOpen, setCameraOpen] = useState(false);
    const [cameraError, setCameraError] = useState<string | null>(null);
    const [formData, setFormData] = useState<WardrobeItemInput>({
        name: '',
        category: 'tops',
        color: '',
        brand: '',
        image: '',
        tags: [],
    });

    const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            const reader = new FileReader();
            reader.onloadend = () => {
                const result = reader.result as string;
                setImagePreview(result);
                setFormData({ ...formData, image: result });
            };
            reader.readAsDataURL(file);
        }
    };

    const stopCamera = useCallback(() => {
        streamRef.current?.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        setCameraOpen(false);
        setCameraError(null);
    }, []);

    const startCamera = useCallback(async () => {
        if (!navigator.mediaDevices?.getUserMedia) {
            cameraInputRef.current?.click();
            return;
        }
        try {
            setCameraError(null);
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } },
                audio: false,
            });
            streamRef.current = stream;
            setCameraOpen(true);
            if (videoRef.current) {
                videoRef.current.srcObject = stream;
            }
        } catch (err) {
            setCameraError('Camera access denied. You can still upload from gallery.');
        }
    }, []);

    const captureFromCamera = useCallback(() => {
        const video = videoRef.current;
        const canvas = captureCanvasRef.current;
        if (!video || !canvas || video.readyState !== 4) return;
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        canvas.toBlob((blob) => {
            if (!blob) return;
            const file = new File([blob], 'wardrobe-camera.jpg', { type: 'image/jpeg' });
            const reader = new FileReader();
            reader.onloadend = () => {
                const result = reader.result as string;
                setImagePreview(result);
                setFormData((prev) => ({ ...prev, image: result }));
                stopCamera();
            };
            reader.readAsDataURL(file);
        }, 'image/jpeg', 0.92);
    }, [stopCamera]);

    useEffect(() => {
        return () => {
            stopCamera();
        };
    }, [stopCamera]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!formData.name || !formData.category || !formData.color) {
            alert('Please fill in all required fields');
            return;
        }

        setIsLoading(true);

        // Simulate processing
        await new Promise(resolve => setTimeout(resolve, 800));

        onSave(formData);

        // Reset form
        setFormData({
            name: '',
            category: 'tops',
            color: '',
            brand: '',
            image: '',
            tags: [],
        });
        setImagePreview(null);
        setIsLoading(false);
        onClose();
    };

    const handleClose = () => {
        setFormData({
            name: '',
            category: 'tops',
            color: '',
            brand: '',
            image: '',
            tags: [],
        });
        setImagePreview(null);
        onClose();
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* Backdrop */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={handleClose}
                        className="fixed inset-0 bg-black/50 z-40"
                    />

                    {/* Chatbot-style Modal */}
                    <motion.div
                        initial={{ opacity: 0, scale: 0.9, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.9, y: 20 }}
                        className="fixed bottom-4 right-4 w-96 max-w-[calc(100vw-2rem)] max-h-[85vh] z-50"
                    >
                        <Card className="shadow-2xl h-full flex flex-col">
                            {/* Chatbot Header */}
                            <CardHeader className="pb-3 flex-shrink-0 bg-gradient-to-r from-accent/20 to-accent/10">
                                <div className="flex items-center justify-between">
                                    <CardTitle className="text-lg flex items-center gap-2">
                                        <div className="w-3 h-3 bg-accent rounded-full animate-pulse" />
                                        Wardrobe Assistant
                                        <Badge variant="outline" className="text-xs">
                                            <Sparkles className="h-3 w-3 mr-1" />
                                            AI Powered
                                        </Badge>
                                    </CardTitle>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={handleClose}
                                        className="h-8 w-8 p-0 flex-shrink-0"
                                    >
                                        <X className="h-4 w-4" />
                                    </Button>
                                </div>
                                <p className="text-sm text-muted-foreground">
                                    Help me organize your wardrobe! Tell me about your item.
                                </p>
                            </CardHeader>

                            {/* Chat-style Form */}
                            <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
                                {/* Image Upload Area */}
                                <div className="bg-muted/30 rounded-lg p-4 border border-dashed border-border">
                                    <label className="block text-sm font-medium mb-3 flex items-center gap-2">
                                        <MessageCircle className="h-4 w-4" />
                                        Show me your item
                                    </label>
                                    <div
                                        className="relative aspect-[3/4] max-w-[180px] mx-auto rounded-xl border-2 border-dashed border-border hover:border-accent transition-colors cursor-pointer overflow-hidden bg-background"
                                        onClick={() => fileInputRef.current?.click()}
                                    >
                                        {imagePreview ? (
                                            <>
                                                <img
                                                    src={imagePreview}
                                                    alt="Preview"
                                                    className="w-full h-full object-cover"
                                                />
                                                <div className="absolute inset-0 bg-accent/20 opacity-0 hover:opacity-100 transition-opacity flex items-center justify-center">
                                                    <p className="text-accent-foreground text-sm font-medium">Click to change</p>
                                                </div>
                                            </>
                                        ) : (
                                            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-muted-foreground">
                                                <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center">
                                                    <Upload className="h-6 w-6" />
                                                </div>
                                                <p className="text-sm text-center px-4">
                                                    Upload a photo
                                                </p>
                                            </div>
                                        )}
                                        <input
                                            ref={fileInputRef}
                                            type="file"
                                            accept="image/*"
                                            onChange={handleImageUpload}
                                            className="hidden"
                                        />
                                        <input
                                            ref={cameraInputRef}
                                            type="file"
                                            accept="image/*"
                                            capture="environment"
                                            onChange={handleImageUpload}
                                            className="hidden"
                                        />
                                    </div>
                                    <div className="flex justify-center gap-2 mt-3">
                                        <Button
                                            type="button"
                                            variant="outline"
                                            size="sm"
                                            onClick={() => fileInputRef.current?.click()}
                                        >
                                            <Image className="h-3 w-3 mr-1" />
                                            Gallery
                                        </Button>
                                        <Button type="button" variant="outline" size="sm" onClick={startCamera}>
                                            <Camera className="h-3 w-3 mr-1" />
                                            Camera
                                        </Button>
                                    </div>
                                    {cameraOpen && (
                                        <div className="mt-3 rounded-lg border border-border p-3 bg-background space-y-2">
                                            {cameraError ? (
                                                <p className="text-xs text-destructive">{cameraError}</p>
                                            ) : (
                                                <>
                                                    <video ref={videoRef} autoPlay playsInline muted className="w-full max-h-64 object-cover rounded-md" />
                                                    <div className="flex gap-2">
                                                        <Button type="button" size="sm" variant="hero" className="flex-1" onClick={captureFromCamera}>
                                                            Capture
                                                        </Button>
                                                        <Button type="button" size="sm" variant="outline" onClick={stopCamera}>
                                                            Cancel
                                                        </Button>
                                                    </div>
                                                </>
                                            )}
                                        </div>
                                    )}
                                </div>

                                {/* Item Details */}
                                <div className="space-y-4">
                                    {/* Item Name */}
                                    <div>
                                        <label className="block text-sm font-medium mb-2 flex items-center gap-2">
                                            <Sparkles className="h-4 w-4" />
                                            What's this item called?
                                        </label>
                                        <input
                                            type="text"
                                            required
                                            value={formData.name}
                                            onChange={e => setFormData({ ...formData, name: e.target.value })}
                                            placeholder="e.g., Blue Denim Jacket"
                                            className="w-full px-4 py-3 bg-background border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent/50"
                                        />
                                    </div>

                                    {/* Category */}
                                    <div>
                                        <label className="block text-sm font-medium mb-2">
                                            What type of item is this?
                                        </label>
                                        <div className="relative">
                                            <select
                                                value={formData.category}
                                                onChange={e => setFormData({ ...formData, category: e.target.value as ProductCategory })}
                                                className="w-full px-4 py-3 bg-background border border-border rounded-lg appearance-none focus:outline-none focus:ring-2 focus:ring-accent/50"
                                            >
                                                {categories.map(cat => (
                                                    <option key={cat.value} value={cat.value}>{cat.label}</option>
                                                ))}
                                            </select>
                                            <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
                                        </div>
                                    </div>

                                    {/* Color */}
                                    <div>
                                        <label className="block text-sm font-medium mb-3">
                                            What color is it? <span className="text-muted-foreground">({formData.color || 'Select one'})</span>
                                        </label>
                                        <div className="flex flex-wrap gap-2">
                                            {colors.map(color => (
                                                <button
                                                    key={color.name}
                                                    type="button"
                                                    onClick={() => setFormData({ ...formData, color: color.name })}
                                                    className={`w-10 h-10 rounded-full border-2 transition-all flex items-center justify-center ${formData.color === color.name
                                                            ? 'border-accent ring-2 ring-accent/20'
                                                            : 'border-transparent hover:border-muted-foreground'
                                                        }`}
                                                    style={{ backgroundColor: color.hex }}
                                                    title={color.name}
                                                >
                                                    {formData.color === color.name && (
                                                        <Check className={`h-5 w-5 ${color.name === 'White' || color.name === 'Beige' ? 'text-charcoal' : 'text-white'}`} />
                                                    )}
                                                </button>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Brand */}
                                    <div>
                                        <label className="block text-sm font-medium mb-3">
                                            Which brand is it?
                                        </label>
                                        <div className="flex flex-wrap gap-2">
                                            {popularBrands.map(brand => (
                                                <button
                                                    key={brand}
                                                    type="button"
                                                    onClick={() => setFormData({ ...formData, brand })}
                                                    className={`px-3 py-1.5 rounded-full text-sm transition-all ${formData.brand === brand
                                                            ? 'bg-accent text-accent-foreground'
                                                            : 'bg-muted hover:bg-muted/80'
                                                        }`}
                                                >
                                                    {brand}
                                                </button>
                                            ))}
                                        </div>
                                        {formData.brand === 'Other' && (
                                            <input
                                                type="text"
                                                placeholder="Enter brand name"
                                                className="w-full mt-3 px-4 py-2 bg-background border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent/50"
                                                onChange={e => setFormData({ ...formData, brand: e.target.value })}
                                            />
                                        )}
                                    </div>
                                </div>

                                {/* Action Buttons */}
                                <div className="flex gap-2 pt-2">
                                    <Button
                                        type="button"
                                        variant="outline"
                                        className="flex-1"
                                        onClick={handleClose}
                                    >
                                        Cancel
                                    </Button>
                                    <Button
                                        type="submit"
                                        variant="hero"
                                        className="flex-1"
                                        disabled={isLoading}
                                        onClick={handleSubmit}
                                    >
                                        {isLoading ? (
                                            <span className="flex items-center gap-2">
                                                <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                                                Saving...
                                            </span>
                                        ) : (
                                            <>
                                                <Check className="h-4 w-4 mr-2" />
                                                Add to Wardrobe
                                            </>
                                        )}
                                    </Button>
                                </div>
                            </CardContent>
                        </Card>
                        <canvas ref={captureCanvasRef} className="hidden" />
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
