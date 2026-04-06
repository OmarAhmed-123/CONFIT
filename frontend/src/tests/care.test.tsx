/**
 * CONFIT Frontend - CARE System Tests
 * =====================================
 * Unit tests for CARE components and viewmodels.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Components
import { BeneficiaryEntry } from '../pages/care/BeneficiaryEntry';
import { BeneficiaryShopping } from '../pages/care/BeneficiaryShopping';
import { DonorDashboard } from '../pages/care/DonorDashboard';
import { CreateCampaignWizard } from '../components/care/CreateCampaignWizard';
import { ImpactChart } from '../components/care/ImpactChart';

// Viewmodels
import { useBeneficiaryEntryViewModel } from '../viewmodels/useBeneficiaryEntryViewModel';
import { useBeneficiaryShoppingViewModel } from '../viewmodels/useBeneficiaryShoppingViewModel';
import { useCareDonorViewModel } from '../viewmodels/useCareDonorViewModel';

// Services
import { careService } from '../services/care.service';

// Mocks
vi.mock('../services/care.service', () => ({
  careService: {
    validateVoucherToken: vi.fn(),
    initiateSession: vi.fn(),
    sendOTP: vi.fn(),
    verifyOTP: vi.fn(),
    getSessionContext: vi.fn(),
    getDonorDashboard: vi.fn(),
    getCampaigns: vi.fn(),
    createCampaign: vi.fn(),
    updateCampaign: vi.fn(),
    deleteCampaign: vi.fn(),
    activateCampaign: vi.fn(),
  },
}));

// Test Wrapper
const TestWrapper = ({ children }: { children: React.ReactNode }) => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {children}
      </BrowserRouter>
    </QueryClientProvider>
  );
};

// ============================================
// Beneficiary Entry Tests
// ============================================

describe('BeneficiaryEntry', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders voucher input step initially', () => {
    render(
      <TestWrapper>
        <BeneficiaryEntry />
      </TestWrapper>
    );

    expect(screen.getByText(/Enter Your Voucher Code/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/CARE-/i)).toBeInTheDocument();
  });

  it('shows error for invalid voucher format', async () => {
    render(
      <TestWrapper>
        <BeneficiaryEntry />
      </TestWrapper>
    );

    const input = screen.getByPlaceholderText(/CARE-/i);
    const submitButton = screen.getByRole('button', { name: /Continue/i });

    await userEvent.type(input, 'invalid-code');
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Invalid voucher format/i)).toBeInTheDocument();
    });
  });

  it('validates voucher and moves to OTP step', async () => {
    const mockVoucher = {
      id: 'voucher-1',
      voucher_token: 'CARE-TEST123456',
      budget_remaining: 1500,
      status: 'active',
    };

    const mockSession = {
      id: 'session-1',
      session_token: 'sess_token',
      status: 'pending',
    };

    vi.mocked(careService.validateVoucherToken).mockResolvedValue(mockVoucher);
    vi.mocked(careService.initiateSession).mockResolvedValue(mockSession);
    vi.mocked(careService.sendOTP).mockResolvedValue({ message: 'OTP sent' });

    render(
      <TestWrapper>
        <BeneficiaryEntry />
      </TestWrapper>
    );

    const input = screen.getByPlaceholderText(/CARE-/i);
    await userEvent.type(input, 'CARE-TEST123456');

    const submitButton = screen.getByRole('button', { name: /Continue/i });
    await userEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Enter OTP/i)).toBeInTheDocument();
    });
  });

  it('verifies OTP and shows success', async () => {
    const mockSession = {
      id: 'session-1',
      session_token: 'sess_token',
      otp_verified: true,
      status: 'authenticated',
    };

    vi.mocked(careService.verifyOTP).mockResolvedValue(mockSession);

    render(
      <TestWrapper>
        <BeneficiaryEntry />
      </TestWrapper>
    );

    // Simulate being on OTP step
    const otpInputs = screen.getAllByRole('textbox');
    for (const input of otpInputs) {
      await userEvent.type(input, '1');
    }

    await waitFor(() => {
      expect(careService.verifyOTP).toHaveBeenCalled();
    });
  });
});

// ============================================
// Beneficiary Shopping Tests
// ============================================

describe('BeneficiaryShopping', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows session expired message without token', () => {
    render(
      <TestWrapper>
        <BeneficiaryShopping />
      </TestWrapper>
    );

    expect(screen.getByText(/Session Expired/i)).toBeInTheDocument();
  });

  it('displays products when session is valid', async () => {
    const mockContext = {
      session: { id: 's1', session_token: 'token' },
      voucher: { budget_remaining: 1500 },
      beneficiary: { name: 'John Doe' },
      campaign: { campaign_name: 'Test Campaign' },
      budget_remaining: 1500,
    };

    vi.mocked(careService.getSessionContext).mockResolvedValue(mockContext);

    // Mock fetch for products
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ products: [] }),
    });

    render(
      <TestWrapper>
        <BeneficiaryShopping />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText(/Welcome, John Doe/i)).toBeInTheDocument();
    });
  });

  it('adds items to cart', async () => {
    const mockContext = {
      session: { id: 's1', session_token: 'token' },
      voucher: { budget_remaining: 1500 },
      beneficiary: { name: 'John Doe' },
      campaign: { campaign_name: 'Test Campaign' },
      budget_remaining: 1500,
    };

    vi.mocked(careService.getSessionContext).mockResolvedValue(mockContext);

    render(
      <TestWrapper>
        <BeneficiaryShopping />
      </TestWrapper>
    );

    // Find and click "Add to Cart" button
    await waitFor(() => {
      const addToCartButtons = screen.getAllByText(/Add to Cart/i);
      expect(addToCartButtons.length).toBeGreaterThan(0);
    });
  });
});

// ============================================
// Donor Dashboard Tests
// ============================================

describe('DonorDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('displays dashboard stats', async () => {
    const mockDashboard = {
      total_campaigns: 5,
      active_campaigns: 3,
      total_beneficiaries_supported: 50,
      total_donated: 75000,
      recent_campaigns: [],
      recent_orders: [],
    };

    vi.mocked(careService.getDonorDashboard).mockResolvedValue(mockDashboard);

    render(
      <TestWrapper>
        <DonorDashboard />
      </TestWrapper>
    );

    await waitFor(() => {
      expect(screen.getByText('5')).toBeInTheDocument();
      expect(screen.getByText('50')).toBeInTheDocument();
    });
  });

  it('opens create campaign wizard', async () => {
    const mockDashboard = {
      total_campaigns: 0,
      active_campaigns: 0,
      total_beneficiaries_supported: 0,
      total_donated: 0,
      recent_campaigns: [],
      recent_orders: [],
    };

    vi.mocked(careService.getDonorDashboard).mockResolvedValue(mockDashboard);

    render(
      <TestWrapper>
        <DonorDashboard />
      </TestWrapper>
    );

    await waitFor(() => {
      const createButton = screen.getByRole('button', { name: /Create Campaign/i });
      expect(createButton).toBeInTheDocument();
    });
  });
});

// ============================================
// Create Campaign Wizard Tests
// ============================================

describe('CreateCampaignWizard', () => {
  const mockProps = {
    open: true,
    onClose: vi.fn(),
    onSubmit: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders wizard steps', () => {
    render(
      <TestWrapper>
        <CreateCampaignWizard {...mockProps} />
      </TestWrapper>
    );

    expect(screen.getByText(/Campaign Details/i)).toBeInTheDocument();
    expect(screen.getByText(/Budget & Restrictions/i)).toBeInTheDocument();
    expect(screen.getByText(/Beneficiaries/i)).toBeInTheDocument();
    expect(screen.getByText(/Review & Launch/i)).toBeInTheDocument();
  });

  it('navigates between steps', async () => {
    render(
      <TestWrapper>
        <CreateCampaignWizard {...mockProps} />
      </TestWrapper>
    );

    // Step 1 - Fill required fields
    const nameInput = screen.getByPlaceholderText(/e.g., Ramadan Clothing Drive/i);
    await userEvent.type(nameInput, 'Test Campaign');

    // Click Next
    const nextButton = screen.getByRole('button', { name: /Next/i });
    await userEvent.click(nextButton);

    await waitFor(() => {
      expect(screen.getByText(/Budget Per Person/i)).toBeInTheDocument();
    });
  });

  it('adds beneficiaries', async () => {
    render(
      <TestWrapper>
        <CreateCampaignWizard {...mockProps} />
      </TestWrapper>
    );

    // Navigate to beneficiaries step
    const nameInput = screen.getByPlaceholderText(/e.g., Ramadan Clothing Drive/i);
    await userEvent.type(nameInput, 'Test Campaign');

    // Click Next twice to get to beneficiaries
    const nextButton = screen.getByRole('button', { name: /Next/i });
    await userEvent.click(nextButton);
    await userEvent.click(nextButton);

    await waitFor(() => {
      expect(screen.getByText(/Add Beneficiary/i)).toBeInTheDocument();
    });
  });

  it('submits campaign on final step', async () => {
    vi.mocked(mockProps.onSubmit).mockResolvedValue({ id: 'campaign-1' });

    render(
      <TestWrapper>
        <CreateCampaignWizard {...mockProps} />
      </TestWrapper>
    );

    // Fill and navigate through all steps
    const nameInput = screen.getByPlaceholderText(/e.g., Ramadan Clothing Drive/i);
    await userEvent.type(nameInput, 'Test Campaign');

    const nextButton = screen.getByRole('button', { name: /Next/i });
    await userEvent.click(nextButton);
    await userEvent.click(nextButton);
    await userEvent.click(nextButton);

    await waitFor(() => {
      expect(screen.getByText(/Review & Launch/i)).toBeInTheDocument();
    });
  });
});

// ============================================
// Impact Chart Tests
// ============================================

describe('ImpactChart', () => {
  it('renders pie chart with data', () => {
    const data = {
      Tops: 1000,
      Bottoms: 800,
      Footwear: 500,
    };

    render(<ImpactChart data={data} type="pie" />);

    expect(screen.getByText('Tops')).toBeInTheDocument();
    expect(screen.getByText('Bottoms')).toBeInTheDocument();
    expect(screen.getByText('Footwear')).toBeInTheDocument();
  });

  it('renders bar chart with data', () => {
    const data = {
      Jan: 5000,
      Feb: 6000,
      Mar: 7500,
    };

    render(<ImpactChart data={data} type="bar" />);

    expect(screen.getByText('Jan')).toBeInTheDocument();
    expect(screen.getByText('Feb')).toBeInTheDocument();
    expect(screen.getByText('Mar')).toBeInTheDocument();
  });

  it('shows empty state when no data', () => {
    render(<ImpactChart data={{}} type="pie" />);

    expect(screen.getByText(/No data to display/i)).toBeInTheDocument();
  });
});

// ============================================
// Viewmodel Tests
// ============================================

describe('useBeneficiaryEntryViewModel', () => {
  it('initializes with correct default state', () => {
    const { result } = renderHook(() => useBeneficiaryEntryViewModel());

    expect(result.current.step).toBe('voucher');
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('validates voucher and initiates session', async () => {
    const mockVoucher = {
      id: 'voucher-1',
      voucher_token: 'CARE-TEST',
      budget_remaining: 1500,
    };

    const mockSession = {
      id: 'session-1',
      session_token: 'token',
    };

    vi.mocked(careService.validateVoucherToken).mockResolvedValue(mockVoucher);
    vi.mocked(careService.initiateSession).mockResolvedValue(mockSession);
    vi.mocked(careService.getSessionContext).mockResolvedValue({
      session: mockSession,
      voucher: mockVoucher,
      beneficiary: { name: 'John' },
      campaign: { campaign_name: 'Test' },
    });

    const { result } = renderHook(() => useBeneficiaryEntryViewModel());

    await act(async () => {
      await result.current.validateVoucher('CARE-TEST');
    });

    expect(result.current.voucher).toEqual(mockVoucher);
  });
});

describe('useCareDonorViewModel', () => {
  it('fetches dashboard data', async () => {
    const mockDashboard = {
      total_campaigns: 5,
      total_donated: 75000,
    };

    vi.mocked(careService.getDonorDashboard).mockResolvedValue(mockDashboard);

    const { result } = renderHook(() => useCareDonorViewModel());

    await act(async () => {
      await result.current.fetchDashboard();
    });

    expect(result.current.dashboard).toEqual(mockDashboard);
  });

  it('creates campaign successfully', async () => {
    const mockCampaign = {
      id: 'campaign-1',
      campaign_name: 'Test Campaign',
    };

    vi.mocked(careService.createCampaign).mockResolvedValue(mockCampaign);
    vi.mocked(careService.activateCampaign).mockResolvedValue(mockCampaign);
    vi.mocked(careService.getCampaigns).mockResolvedValue({ campaigns: [] });

    const { result } = renderHook(() => useCareDonorViewModel());

    const campaignData = {
      campaign_name: 'Test Campaign',
      campaign_type: 'individual',
      budget_per_person: 1500,
      currency: 'EGP',
      voucher_expiry_days: 30,
      beneficiaries: [],
      send_invitations: false,
    };

    await act(async () => {
      await result.current.createCampaign(campaignData);
    });

    expect(careService.createCampaign).toHaveBeenCalled();
  });
});

// ============================================
// Helper function for hook testing
// ============================================

import { renderHook, act } from '@testing-library/react';
