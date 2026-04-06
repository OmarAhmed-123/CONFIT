/**
 * CONFIT CARE - Beneficiary Entry
 * =================================
 * Entry point for beneficiaries to access their shopping voucher.
 * Includes voucher validation and OTP verification.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Heart,
  Gift,
  Lock,
  Phone,
  ArrowRight,
  CheckCircle,
  AlertCircle,
  Loader2,
  Shield,
  Sparkles,
  ShoppingBag,
  Clock,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { careService } from '../../services/care.service';
import { Button } from '../../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { useBeneficiaryEntryViewModel } from '../../viewmodels/useBeneficiaryEntryViewModel';

type Step = 'voucher' | 'otp' | 'success';

export const BeneficiaryEntry: React.FC = () => {
  const navigate = useNavigate();
  const {
    step,
    voucherToken,
    session,
    voucher,
    campaign,
    loading,
    error,
    otpSent,
    otpCode,
    countdown,
    attempts,
    validateVoucher,
    initiateSession,
    sendOTP,
    verifyOTP,
    setVoucherToken,
    setOtpCode,
    reset,
  } = useBeneficiaryEntryViewModel();

  const [voucherError, setVoucherError] = useState<string | null>(null);
  const [otpError, setOtpError] = useState<string | null>(null);

  const handleVoucherSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setVoucherError(null);
    
    try {
      await validateVoucher(voucherToken);
      await initiateSession(voucherToken);
      await sendOTP();
    } catch (err: any) {
      setVoucherError(err.message || 'Invalid voucher token');
    }
  };

  const handleOtpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setOtpError(null);
    
    try {
      await verifyOTP(otpCode);
      // Navigate to shopping on success
      setTimeout(() => {
        navigate(`/care/shop?session=${session?.session_token}`);
      }, 2000);
    } catch (err: any) {
      setOtpError(err.message || 'Invalid OTP code');
    }
  };

  const handleResendOtp = async () => {
    if (countdown > 0) return;
    setOtpError(null);
    try {
      await sendOTP();
    } catch (err: any) {
      setOtpError(err.message || 'Failed to resend OTP');
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-pink-50 flex flex-col">
      {/* Header */}
      <div className="bg-white/80 backdrop-blur-sm border-b border-purple-100">
        <div className="max-w-md mx-auto px-4 py-4">
          <div className="flex items-center justify-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
              <Heart className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
              CONFIT CARE
            </span>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <AnimatePresence mode="wait">
            {/* Step 1: Voucher Entry */}
            {step === 'voucher' && (
              <motion.div
                key="voucher"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
              >
                <Card className="bg-white/90 backdrop-blur-sm shadow-xl border-purple-100">
                  <CardHeader className="text-center pb-2">
                    <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                      <Gift className="w-8 h-8 text-white" />
                    </div>
                    <CardTitle className="text-2xl">Welcome!</CardTitle>
                    <p className="text-gray-500 text-sm mt-2">
                      Enter your voucher code to start shopping
                    </p>
                  </CardHeader>
                  <CardContent>
                    <form onSubmit={handleVoucherSubmit} className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="voucher">Voucher Code</Label>
                        <Input
                          id="voucher"
                          type="text"
                          placeholder="CARE-XXXXXXXXXX"
                          value={voucherToken}
                          onChange={(e) => setVoucherToken(e.target.value.toUpperCase())}
                          className="text-center text-lg tracking-wider font-mono"
                          maxLength={16}
                        />
                        {voucherError && (
                          <p className="text-sm text-red-500 flex items-center gap-1">
                            <AlertCircle className="w-4 h-4" />
                            {voucherError}
                          </p>
                        )}
                      </div>

                      <Button
                        type="submit"
                        className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
                        disabled={loading || !voucherToken}
                      >
                        {loading ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <>
                            Continue
                            <ArrowRight className="w-4 h-4 ml-2" />
                          </>
                        )}
                      </Button>
                    </form>

                    <div className="mt-6 pt-6 border-t border-gray-100">
                      <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
                        <Shield className="w-4 h-4" />
                        <span>Secure & private shopping experience</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            )}

            {/* Step 2: OTP Verification */}
            {step === 'otp' && (
              <motion.div
                key="otp"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
              >
                <Card className="bg-white/90 backdrop-blur-sm shadow-xl border-purple-100">
                  <CardHeader className="text-center pb-2">
                    <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-green-500 to-teal-500 flex items-center justify-center">
                      <Lock className="w-8 h-8 text-white" />
                    </div>
                    <CardTitle className="text-2xl">Verify Your Identity</CardTitle>
                    <p className="text-gray-500 text-sm mt-2">
                      We've sent a 6-digit code to your phone
                    </p>
                  </CardHeader>
                  <CardContent>
                    <form onSubmit={handleOtpSubmit} className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="otp">Verification Code</Label>
                        <div className="flex justify-center gap-2">
                          {[0, 1, 2, 3, 4, 5].map((index) => (
                            <Input
                              key={index}
                              id={`otp-${index}`}
                              type="text"
                              inputMode="numeric"
                              maxLength={1}
                              className="w-12 h-14 text-center text-xl font-bold"
                              value={otpCode[index] || ''}
                              onChange={(e) => {
                                const value = e.target.value.replace(/\D/g, '');
                                const newOtp = otpCode.split('');
                                newOtp[index] = value;
                                setOtpCode(newOtp.join(''));
                                
                                // Auto-focus next input
                                if (value && index < 5) {
                                  const nextInput = document.getElementById(`otp-${index + 1}`);
                                  nextInput?.focus();
                                }
                              }}
                              onKeyDown={(e) => {
                                if (e.key === 'Backspace' && !otpCode[index] && index > 0) {
                                  const prevInput = document.getElementById(`otp-${index - 1}`);
                                  prevInput?.focus();
                                }
                              }}
                            />
                          ))}
                        </div>
                        {otpError && (
                          <p className="text-sm text-red-500 flex items-center justify-center gap-1">
                            <AlertCircle className="w-4 h-4" />
                            {otpError}
                          </p>
                        )}
                        {attempts > 0 && (
                          <p className="text-sm text-yellow-600 text-center">
                            {3 - attempts} attempts remaining
                          </p>
                        )}
                      </div>

                      <Button
                        type="submit"
                        className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
                        disabled={loading || otpCode.length !== 6}
                      >
                        {loading ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <>
                            Verify & Start Shopping
                            <ArrowRight className="w-4 h-4 ml-2" />
                          </>
                        )}
                      </Button>

                      <div className="text-center">
                        <button
                          type="button"
                          onClick={handleResendOtp}
                          disabled={countdown > 0}
                          className="text-sm text-purple-600 hover:text-purple-700 disabled:text-gray-400"
                        >
                          {countdown > 0 ? (
                            <span className="flex items-center justify-center gap-1">
                              <Clock className="w-4 h-4" />
                              Resend in {formatTime(countdown)}
                            </span>
                          ) : (
                            'Resend Code'
                          )}
                        </button>
                      </div>
                    </form>

                    {/* Campaign Preview */}
                    {campaign && (
                      <div className="mt-6 pt-6 border-t border-gray-100">
                        <div className="p-4 rounded-xl bg-gradient-to-r from-purple-50 to-pink-50">
                          <p className="text-sm text-gray-600 text-center">
                            <span className="font-medium">{campaign.campaign_name}</span>
                            <br />
                            <span className="text-purple-600 font-bold">
                              {voucher?.budget_remaining?.toLocaleString()} EGP
                            </span>{' '}
                            available to shop
                          </p>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>
            )}

            {/* Step 3: Success */}
            {step === 'success' && (
              <motion.div
                key="success"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
              >
                <Card className="bg-white/90 backdrop-blur-sm shadow-xl border-green-100">
                  <CardContent className="pt-8 pb-8 text-center">
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ type: 'spring', delay: 0.2 }}
                      className="w-20 h-20 mx-auto mb-6 rounded-full bg-gradient-to-br from-green-500 to-teal-500 flex items-center justify-center"
                    >
                      <CheckCircle className="w-10 h-10 text-white" />
                    </motion.div>
                    
                    <h2 className="text-2xl font-bold text-gray-900 mb-2">
                      You're All Set!
                    </h2>
                    <p className="text-gray-500 mb-6">
                      Redirecting you to your shopping experience...
                    </p>

                    <div className="flex items-center justify-center gap-2 text-purple-600">
                      <Sparkles className="w-5 h-5" />
                      <span className="font-medium">Happy Shopping!</span>
                      <Sparkles className="w-5 h-5" />
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Footer */}
      <div className="bg-white/50 backdrop-blur-sm border-t border-purple-100 py-4">
        <div className="max-w-md mx-auto px-4 text-center text-sm text-gray-500">
          <p>
            Need help? Contact{' '}
            <a href="mailto:care@confit.app" className="text-purple-600 hover:underline">
              care@confit.app
            </a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default BeneficiaryEntry;
