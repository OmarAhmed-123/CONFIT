/**
 * CONFIT CARE - Beneficiary Entry ViewModel
 * ==========================================
 * ViewModel for beneficiary voucher entry and OTP verification.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { careService, Voucher, Campaign, Session, SessionContext } from '../services/care.service';

type Step = 'voucher' | 'otp' | 'success';

interface UseBeneficiaryEntryViewModel {
  // State
  step: Step;
  voucherToken: string;
  session: Session | null;
  voucher: Voucher | null;
  campaign: Campaign | null;
  loading: boolean;
  error: string | null;
  otpSent: boolean;
  otpCode: string;
  countdown: number;
  attempts: number;
  
  // Actions
  setVoucherToken: (token: string) => void;
  setOtpCode: (code: string) => void;
  validateVoucher: (token: string) => Promise<Voucher>;
  initiateSession: (token: string) => Promise<Session>;
  sendOTP: () => Promise<void>;
  verifyOTP: (code: string) => Promise<void>;
  reset: () => void;
}

export const useBeneficiaryEntryViewModel = (): UseBeneficiaryEntryViewModel => {
  const [step, setStep] = useState<Step>('voucher');
  const [voucherToken, setVoucherToken] = useState('');
  const [session, setSession] = useState<Session | null>(null);
  const [voucher, setVoucher] = useState<Voucher | null>(null);
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [otpSent, setOtpSent] = useState(false);
  const [otpCode, setOtpCode] = useState('');
  const [countdown, setCountdown] = useState(0);
  const [attempts, setAttempts] = useState(0);
  
  const countdownRef = useRef<NodeJS.Timeout | null>(null);

  // Countdown timer for OTP resend
  useEffect(() => {
    if (countdown > 0) {
      countdownRef.current = setTimeout(() => {
        setCountdown(prev => prev - 1);
      }, 1000);
    }
    
    return () => {
      if (countdownRef.current) {
        clearTimeout(countdownRef.current);
      }
    };
  }, [countdown]);

  const validateVoucher = useCallback(async (token: string): Promise<Voucher> => {
    setLoading(true);
    setError(null);
    
    try {
      const voucherData = await careService.validateVoucherToken(token);
      setVoucher(voucherData);
      return voucherData;
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || 'Invalid voucher token';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  const initiateSession = useCallback(async (token: string): Promise<Session> => {
    setLoading(true);
    setError(null);
    
    try {
      const sessionData = await careService.initiateSession(token);
      setSession(sessionData);
      
      // Fetch session context for campaign and voucher info
      const context = await careService.getSessionContext(sessionData.session_token);
      setCampaign(context.campaign);
      setVoucher(context.voucher);
      
      setStep('otp');
      return sessionData;
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || 'Failed to initiate session';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  const sendOTP = useCallback(async (): Promise<void> => {
    if (!session) return;
    
    setLoading(true);
    setError(null);
    
    try {
      await careService.sendOTP(session.id);
      setOtpSent(true);
      setCountdown(60); // 60 second countdown
      setOtpCode(''); // Reset OTP input
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || 'Failed to send OTP';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [session]);

  const verifyOTP = useCallback(async (code: string): Promise<void> => {
    if (!session) return;
    
    setLoading(true);
    setError(null);
    
    try {
      await careService.verifyOTP(session.id, code);
      setStep('success');
      setAttempts(0);
    } catch (err: any) {
      const errorMessage = err.response?.data?.message || err.message || 'Invalid OTP code';
      setError(errorMessage);
      setAttempts(prev => prev + 1);
      
      // Check if session is locked
      if (attempts >= 2) {
        setError('Too many failed attempts. Please try again later.');
        setStep('voucher');
        setSession(null);
      }
      
      throw new Error(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [session, attempts]);

  const reset = useCallback(() => {
    setStep('voucher');
    setVoucherToken('');
    setSession(null);
    setVoucher(null);
    setCampaign(null);
    setLoading(false);
    setError(null);
    setOtpSent(false);
    setOtpCode('');
    setCountdown(0);
    setAttempts(0);
  }, []);

  return {
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
    setVoucherToken,
    setOtpCode,
    validateVoucher,
    initiateSession,
    sendOTP,
    verifyOTP,
    reset,
  };
};

export default useBeneficiaryEntryViewModel;
