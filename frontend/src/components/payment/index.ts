/**
 * Payment Components - Egypt Payment UI Wiring (Phase C)
 * 
 * Exports all Egypt-specific payment components for checkout integration.
 * 
 * @module @/components/payment
 */

// Payment Method Selector
export { 
  PaymentMethodSelector,
  type EgyptPaymentMethod,
  type PaymentProvider,
  type PaymentCategory,
  type PaymentMethodOption,
  type PaymentMethodSelectorProps,
} from './PaymentMethodSelector';

// Paymob Iframe Wrapper
export { 
  PaymobIframe,
  usePaymobPayment,
  type PaymobIframeProps,
  type PaymobPaymentStatus,
  type PaymobCallbackData,
} from './PaymobIframe';

// Fawry Reference Display
export { 
  FawryReference,
  useFawryReference,
  type FawryReferenceProps,
  type ExpiryStatus,
} from './FawryReference';

// Valu BNPL Calculator
export { 
  ValuCalculator,
  useValuCalculator,
  type ValuCalculatorProps,
  type ValuCalculation,
  type ValuTenor,
  type ValuEligibilityResult,
} from './ValuCalculator';
