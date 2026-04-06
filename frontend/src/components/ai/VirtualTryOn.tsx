/**
 * CONFIT Frontend - Virtual Try-On Component
 * MIRROR virtual try-on interface
 */

'use client';

import React, { useState, useRef } from 'react';
import './ai-components.css';
import { useMirror } from '@/hooks/useMirror';
import { 
  Camera, Upload, Loader2, Check, X, 
  RefreshCw, ShoppingBag, AlertCircle 
} from 'lucide-react';

interface VirtualTryOnProps {
  productId: string;
  productSku: string;
  productName: string;
  productImage: string;
  productPrice?: number;
  onAddToBag?: () => void;
  onClose?: () => void;
}

export function VirtualTryOn({
  productId,
  productSku,
  productName,
  productImage,
  productPrice,
  onAddToBag,
  onClose,
}: VirtualTryOnProps) {
  const {
    currentSession,
    isUploading,
    isProcessing,
    error,
    startTryOn,
  } = useMirror({
    onComplete: (session) => {
      console.log('Try-on completed:', session);
    },
  });

  const [personImage, setPersonImage] = useState<string | null>(null);
  const [personFile, setPersonFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file
    if (!file.type.startsWith('image/')) {
      alert('Please select an image file');
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      alert('Image must be less than 10MB');
      return;
    }

    setPersonFile(file);

    // Create preview
    const reader = new FileReader();
    reader.onload = (e) => {
      setPersonImage(e.target?.result as string);
    };
    reader.readAsDataURL(file);
  };

  const handleStartTryOn = async () => {
    if (!personFile) return;

    await startTryOn(productId, productSku, personFile);
  };

  const handleReset = () => {
    setPersonImage(null);
    setPersonFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-xl max-w-lg mx-auto overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b bg-gradient-to-r from-blue-600 to-cyan-500 text-white">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
            <Camera className="w-5 h-5" />
          </div>
          <div>
            <h2 className="font-semibold">MIRROR</h2>
            <p className="text-xs text-white/80">Virtual Try-On</p>
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="p-2 hover:bg-white/20 rounded-full transition-colors"
            title="Close"
            aria-label="Close try-on"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Product Info */}
        <div className="flex items-center gap-3 mb-4 p-3 bg-gray-50 rounded-lg">
          <img
            src={productImage}
            alt={productName}
            className="w-16 h-16 object-cover rounded-lg"
          />
          <div className="flex-1">
            <p className="font-medium text-sm">{productName}</p>
            {productPrice && (
              <p className="text-sm text-gray-600">${productPrice.toFixed(2)}</p>
            )}
          </div>
        </div>

        {/* Photo Upload */}
        {!currentSession?.result_url && (
          <div className="space-y-4">
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-gray-300 rounded-xl p-6 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50/50 transition-colors"
            >
              {personImage ? (
                <div className="relative">
                  <img
                    src={personImage}
                    alt="Your photo"
                    className="w-32 h-32 object-cover rounded-lg mx-auto"
                  />
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleReset();
                    }}
                    className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full p-1"
                    title="Remove photo"
                    aria-label="Remove photo"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ) : (
                <>
                  <Upload className="w-8 h-8 mx-auto text-gray-400 mb-2" />
                  <p className="text-sm text-gray-600">
                    Upload your photo to try on
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    JPG, PNG up to 10MB
                  </p>
                </>
              )}
            </div>

            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleFileSelect}
              className="hidden"
              aria-label="Upload your photo"
              title="Upload your photo"
            />

            {/* Start Button */}
            <button
              onClick={handleStartTryOn}
              disabled={!personFile || isUploading || isProcessing}
              className="w-full py-3 bg-gradient-to-r from-blue-600 to-cyan-500 text-white rounded-lg font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity flex items-center justify-center gap-2"
            >
              {(isUploading || isProcessing) ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Camera className="w-4 h-4" />
                  Try It On
                </>
              )}
            </button>
          </div>
        )}

        {/* Processing State */}
        {isProcessing && !currentSession?.result_url && (
          <div className="text-center py-8">
            <Loader2 className="w-12 h-12 animate-spin text-blue-600 mx-auto mb-4" />
            <p className="text-sm text-gray-600">
              AI is processing your try-on...
            </p>
            <p className="text-xs text-gray-400 mt-1">
              This may take 30-60 seconds
            </p>
          </div>
        )}

        {/* Result */}
        {currentSession?.result_url && (
          <div className="space-y-4">
            <div className="relative rounded-xl overflow-hidden">
              <img
                src={currentSession.result_url}
                alt="Try-on result"
                className="w-full aspect-[3/4] object-cover"
              />
              <div className="absolute top-3 right-3 bg-green-500 text-white px-3 py-1 rounded-full text-xs font-medium flex items-center gap-1">
                <Check className="w-3 h-3" />
                Completed
              </div>
            </div>

            {/* Quality Score */}
            {currentSession.quality_score > 0 && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-600">Quality Score</span>
                <div className="flex items-center gap-2">
                  <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className="quality-bar-fill"
                      style={{ width: `${Math.round(currentSession.quality_score * 100)}%` }}
                    />
                  </div>
                  <span className="text-gray-800 font-medium">
                    {Math.round(currentSession.quality_score * 100)}%
                  </span>
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3">
              <button
                onClick={handleReset}
                className="flex-1 py-2 border border-gray-300 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors flex items-center justify-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                Try Again
              </button>
              {onAddToBag && (
                <button
                  onClick={onAddToBag}
                  className="flex-1 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
                >
                  <ShoppingBag className="w-4 h-4" />
                  Add to Bag
                </button>
              )}
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="flex items-center gap-2 p-3 bg-red-50 text-red-600 rounded-lg">
            <AlertCircle className="w-4 h-4" />
            <p className="text-sm">{error}</p>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 bg-gray-50 border-t text-center">
        <p className="text-xs text-gray-500">
          Your photo is encrypted and deleted after 30 days
        </p>
      </div>
    </div>
  );
}

export default VirtualTryOn;
