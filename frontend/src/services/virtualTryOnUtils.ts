/**
 * Virtual Try-On Utilities
 * 
 * This module provides utility functions for the virtual try-on feature,
 * including image processing, garment placement calculations, and canvas rendering.
 */

// Types for Virtual Try-On
export interface TryOnPosition {
    x: number;
    y: number;
    scale: number;
    rotation: number;
}

export interface GarmentPlacement {
    x: number;
    y: number;
    width: number;
    height: number;
    rotation: number;
}

export interface ImageDimensions {
    width: number;
    height: number;
    aspectRatio: number;
}

export type GarmentCategory = 'tops' | 'bottoms' | 'dresses' | 'outerwear' | 'shoes' | 'accessories' | 'bags';

export type FitType = 'tight' | 'regular' | 'loose';

export interface TryOnConfig {
    blendMode: GlobalCompositeOperation;
    opacity: number;
    shadowBlur: number;
    shadowColor: string;
    shadowOffsetX: number;
    shadowOffsetY: number;
}

// Default configurations per garment category
const CATEGORY_CONFIGS: Record<GarmentCategory, TryOnConfig> = {
    tops: {
        blendMode: 'multiply',
        opacity: 0.92,
        shadowBlur: 15,
        shadowColor: 'rgba(0, 0, 0, 0.25)',
        shadowOffsetX: 3,
        shadowOffsetY: 5,
    },
    bottoms: {
        blendMode: 'multiply',
        opacity: 0.90,
        shadowBlur: 12,
        shadowColor: 'rgba(0, 0, 0, 0.22)',
        shadowOffsetX: 2,
        shadowOffsetY: 4,
    },
    dresses: {
        blendMode: 'multiply',
        opacity: 0.93,
        shadowBlur: 18,
        shadowColor: 'rgba(0, 0, 0, 0.28)',
        shadowOffsetX: 3,
        shadowOffsetY: 6,
    },
    outerwear: {
        blendMode: 'multiply',
        opacity: 0.88,
        shadowBlur: 20,
        shadowColor: 'rgba(0, 0, 0, 0.30)',
        shadowOffsetX: 4,
        shadowOffsetY: 7,
    },
    shoes: {
        blendMode: 'multiply',
        opacity: 0.95,
        shadowBlur: 8,
        shadowColor: 'rgba(0, 0, 0, 0.20)',
        shadowOffsetX: 2,
        shadowOffsetY: 3,
    },
    accessories: {
        blendMode: 'source-over',
        opacity: 0.95,
        shadowBlur: 5,
        shadowColor: 'rgba(0, 0, 0, 0.15)',
        shadowOffsetX: 1,
        shadowOffsetY: 2,
    },
    bags: {
        blendMode: 'source-over',
        opacity: 0.95,
        shadowBlur: 10,
        shadowColor: 'rgba(0, 0, 0, 0.20)',
        shadowOffsetX: 2,
        shadowOffsetY: 4,
    },
};

// Placement ratios for different garment categories (relative to canvas)
const PLACEMENT_RATIOS: Record<GarmentCategory, { yRatio: number; widthRatio: number; heightRatio: number }> = {
    tops: { yRatio: 0.15, widthRatio: 0.50, heightRatio: 0.40 },
    bottoms: { yRatio: 0.45, widthRatio: 0.45, heightRatio: 0.45 },
    dresses: { yRatio: 0.12, widthRatio: 0.55, heightRatio: 0.70 },
    outerwear: { yRatio: 0.10, widthRatio: 0.55, heightRatio: 0.50 },
    shoes: { yRatio: 0.80, widthRatio: 0.30, heightRatio: 0.15 },
    accessories: { yRatio: 0.05, widthRatio: 0.20, heightRatio: 0.15 },
    bags: { yRatio: 0.40, widthRatio: 0.25, heightRatio: 0.30 },
};

// Fit multipliers
const FIT_MULTIPLIERS: Record<FitType, number> = {
    tight: 0.88,
    regular: 1.0,
    loose: 1.15,
};

/**
 * Load an image from a URL or data URI and return as HTMLImageElement
 */
export function loadImage(src: string): Promise<HTMLImageElement> {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.crossOrigin = 'anonymous';
        img.onload = () => resolve(img);
        img.onerror = (error) => reject(new Error(`Failed to load image: ${error}`));
        img.src = src;
    });
}

/**
 * Get dimensions of an image
 */
export function getImageDimensions(img: HTMLImageElement): ImageDimensions {
    return {
        width: img.naturalWidth,
        height: img.naturalHeight,
        aspectRatio: img.naturalWidth / img.naturalHeight,
    };
}

/**
 * Calculate optimal garment placement based on category and canvas size
 */
export function calculateGarmentPlacement(
    canvasWidth: number,
    canvasHeight: number,
    garmentDimensions: ImageDimensions,
    category: GarmentCategory,
    position: TryOnPosition,
    fitType: FitType = 'regular'
): GarmentPlacement {
    const ratios = PLACEMENT_RATIOS[category];
    const fitMultiplier = FIT_MULTIPLIERS[fitType];

    // Calculate base dimensions with better aspect ratio preservation
    const canvasAspectRatio = canvasWidth / canvasHeight;
    const garmentAspectRatio = garmentDimensions.aspectRatio;
    
    // Smart scaling based on body proportions
    let baseWidth = canvasWidth * ratios.widthRatio * fitMultiplier;
    let baseHeight = baseWidth / garmentAspectRatio;
    
    // Adjust for very tall or wide images
    if (canvasAspectRatio > 1.5) {
        // Wide image - reduce width slightly
        baseWidth = canvasWidth * ratios.widthRatio * 0.9 * fitMultiplier;
        baseHeight = baseWidth / garmentAspectRatio;
    } else if (canvasAspectRatio < 0.7) {
        // Tall image - adjust height
        baseHeight = canvasHeight * ratios.heightRatio * 0.9 * fitMultiplier;
        baseWidth = baseHeight * garmentAspectRatio;
    }

    // Apply user scale with limits
    const userScale = Math.max(0.5, Math.min(2.0, position.scale));
    const scaledWidth = baseWidth * userScale;
    const scaledHeight = baseHeight * userScale;

    // Calculate position with intelligent centering
    const centerX = canvasWidth / 2;
    const baseY = canvasHeight * ratios.yRatio;
    
    // Add slight offset based on category for more natural placement
    const categoryOffset = {
        tops: -10,
        bottoms: 5,
        dresses: -5,
        outerwear: -8,
        shoes: 0,
        accessories: -15,
        bags: 10
    }[category] || 0;

    return {
        x: centerX - scaledWidth / 2 + (position.x || 0),
        y: baseY + categoryOffset + (position.y || 0),
        width: scaledWidth,
        height: scaledHeight,
        rotation: position.rotation || 0,
    };
}

/**
 * Apply perspective transform to give depth to the garment
 */
export function applyPerspectiveTransform(
    ctx: CanvasRenderingContext2D,
    placement: GarmentPlacement,
    category: GarmentCategory
): void {
    const centerX = placement.x + placement.width / 2;
    const centerY = placement.y + placement.height / 2;

    ctx.translate(centerX, centerY);
    ctx.rotate((placement.rotation * Math.PI) / 180);

    // Apply subtle perspective based on category
    if (category === 'tops' || category === 'dresses' || category === 'outerwear') {
        // Slight taper at bottom for tops
        ctx.transform(1, 0, 0, 1, 0, 0);
    }

    ctx.translate(-centerX, -centerY);
}

/**
 * Apply garment to canvas with realistic rendering
 */
export async function applyGarmentToCanvas(
    canvas: HTMLCanvasElement,
    userImage: HTMLImageElement,
    garmentImage: HTMLImageElement,
    category: GarmentCategory,
    position: TryOnPosition,
    fitType: FitType = 'regular'
): Promise<void> {
    const ctx = canvas.getContext('2d');
    if (!ctx) {
        throw new Error('Failed to get canvas context');
    }

    const config = CATEGORY_CONFIGS[category];
    const garmentDimensions = getImageDimensions(garmentImage);

    // Clear and draw user image
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(userImage, 0, 0, canvas.width, canvas.height);

    // Calculate placement
    const placement = calculateGarmentPlacement(
        canvas.width,
        canvas.height,
        garmentDimensions,
        category,
        position,
        fitType
    );

    // Save context state
    ctx.save();

    // Apply transforms
    applyPerspectiveTransform(ctx, placement, category);

    // Apply shadow
    ctx.shadowBlur = config.shadowBlur;
    ctx.shadowColor = config.shadowColor;
    ctx.shadowOffsetX = config.shadowOffsetX;
    ctx.shadowOffsetY = config.shadowOffsetY;

    // Draw shadow layer first (on a transparent layer)
    ctx.globalAlpha = 0.4;
    ctx.drawImage(
        garmentImage,
        placement.x + 2,
        placement.y + 4,
        placement.width,
        placement.height
    );

    // Reset shadow
    ctx.shadowBlur = 0;
    ctx.shadowOffsetX = 0;
    ctx.shadowOffsetY = 0;

    // Apply blend mode and opacity for main garment
    ctx.globalCompositeOperation = config.blendMode;
    ctx.globalAlpha = config.opacity;

    // Draw the garment
    ctx.drawImage(
        garmentImage,
        placement.x,
        placement.y,
        placement.width,
        placement.height
    );

    // Add highlight layer for fabric effect
    ctx.globalCompositeOperation = 'overlay';
    ctx.globalAlpha = 0.1;
    ctx.drawImage(
        garmentImage,
        placement.x,
        placement.y,
        placement.width,
        placement.height
    );

    // Restore context state
    ctx.restore();
}

/**
 * Generate the final try-on result as a data URL
 */
export function generateTryOnResult(canvas: HTMLCanvasElement, quality: number = 0.92): string {
    return canvas.toDataURL('image/jpeg', quality);
}

/**
 * Download the try-on result as an image file
 */
export function downloadTryOnResult(canvas: HTMLCanvasElement, filename: string = 'try-on-result.jpg'): void {
    const link = document.createElement('a');
    link.download = filename;
    link.href = generateTryOnResult(canvas);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

/**
 * Process and optimize an image for try-on (resize if too large)
 */
export async function processImageForTryOn(
    imageSrc: string,
    maxWidth: number = 1200,
    maxHeight: number = 1600
): Promise<string> {
    const img = await loadImage(imageSrc);
    const dimensions = getImageDimensions(img);

    // Check if resizing is needed
    if (dimensions.width <= maxWidth && dimensions.height <= maxHeight) {
        return imageSrc;
    }

    // Calculate new dimensions maintaining aspect ratio
    let newWidth = dimensions.width;
    let newHeight = dimensions.height;

    if (newWidth > maxWidth) {
        newWidth = maxWidth;
        newHeight = newWidth / dimensions.aspectRatio;
    }

    if (newHeight > maxHeight) {
        newHeight = maxHeight;
        newWidth = newHeight * dimensions.aspectRatio;
    }

    // Create canvas and resize
    const canvas = document.createElement('canvas');
    canvas.width = newWidth;
    canvas.height = newHeight;

    const ctx = canvas.getContext('2d');
    if (!ctx) {
        throw new Error('Failed to get canvas context');
    }

    // Use high-quality image smoothing
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';

    ctx.drawImage(img, 0, 0, newWidth, newHeight);

    return canvas.toDataURL('image/jpeg', 0.92);
}

/**
 * Detect approximate body region for smarter placement
 * This is a simplified detection based on image analysis
 */
export function detectBodyRegion(
    canvas: HTMLCanvasElement
): { topY: number; bottomY: number; centerX: number } {
    const ctx = canvas.getContext('2d');
    if (!ctx) {
        return { topY: canvas.height * 0.1, bottomY: canvas.height * 0.9, centerX: canvas.width / 2 };
    }

    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const data = imageData.data;

    let topY = canvas.height;
    let bottomY = 0;
    let leftX = canvas.width;
    let rightX = 0;

    // Scan for non-background pixels (simplified skin/clothing detection)
    for (let y = 0; y < canvas.height; y++) {
        for (let x = 0; x < canvas.width; x++) {
            const i = (y * canvas.width + x) * 4;
            const r = data[i];
            const g = data[i + 1];
            const b = data[i + 2];

            // Check if pixel is likely part of a person (not pure white/black background)
            const brightness = (r + g + b) / 3;
            if (brightness > 20 && brightness < 240) {
                if (y < topY) topY = y;
                if (y > bottomY) bottomY = y;
                if (x < leftX) leftX = x;
                if (x > rightX) rightX = x;
            }
        }
    }

    // Add padding
    topY = Math.max(0, topY - 10);
    bottomY = Math.min(canvas.height, bottomY + 10);

    return {
        topY,
        bottomY,
        centerX: (leftX + rightX) / 2,
    };
}

/**
 * Create a comparison slider effect between two images
 */
export function createComparisonCanvas(
    originalCanvas: HTMLCanvasElement,
    resultCanvas: HTMLCanvasElement,
    sliderPosition: number // 0 to 1
): HTMLCanvasElement {
    const comparisonCanvas = document.createElement('canvas');
    comparisonCanvas.width = originalCanvas.width;
    comparisonCanvas.height = originalCanvas.height;

    const ctx = comparisonCanvas.getContext('2d');
    if (!ctx) {
        return comparisonCanvas;
    }

    const splitX = comparisonCanvas.width * sliderPosition;

    // Draw original on left side
    ctx.save();
    ctx.beginPath();
    ctx.rect(0, 0, splitX, comparisonCanvas.height);
    ctx.clip();
    ctx.drawImage(originalCanvas, 0, 0);
    ctx.restore();

    // Draw result on right side
    ctx.save();
    ctx.beginPath();
    ctx.rect(splitX, 0, comparisonCanvas.width - splitX, comparisonCanvas.height);
    ctx.clip();
    ctx.drawImage(resultCanvas, 0, 0);
    ctx.restore();

    // Draw divider line
    ctx.strokeStyle = 'white';
    ctx.lineWidth = 3;
    ctx.shadowColor = 'rgba(0, 0, 0, 0.5)';
    ctx.shadowBlur = 5;
    ctx.beginPath();
    ctx.moveTo(splitX, 0);
    ctx.lineTo(splitX, comparisonCanvas.height);
    ctx.stroke();

    return comparisonCanvas;
}

/**
 * Get category from product data
 */
export function getCategoryFromProduct(product: { category?: string }): GarmentCategory {
    const category = product.category?.toLowerCase() || 'tops';
    const validCategories: GarmentCategory[] = ['tops', 'bottoms', 'dresses', 'outerwear', 'shoes', 'accessories', 'bags'];

    if (validCategories.includes(category as GarmentCategory)) {
        return category as GarmentCategory;
    }

    return 'tops';
}

/**
 * Validate that an image is suitable for try-on
 */
export function validateImageForTryOn(img: HTMLImageElement): { valid: boolean; message: string } {
    const dimensions = getImageDimensions(img);

    if (dimensions.width < 200 || dimensions.height < 300) {
        return {
            valid: false,
            message: 'Image resolution is too low. Please upload a larger image (minimum 200x300 pixels).'
        };
    }

    if (dimensions.aspectRatio > 2 || dimensions.aspectRatio < 0.4) {
        return {
            valid: false,
            message: 'Image aspect ratio is unusual. Please upload a standard portrait photo.'
        };
    }

    return { valid: true, message: 'Image is valid' };
}
