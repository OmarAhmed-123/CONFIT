"""Payment provider adapters."""

from services.payment_platform.base import (
    BaseIntegration,
    PaymentProviderError,
    egp_to_piastres,
    piastres_to_egp,
)

from services.payment_platform.providers.paymob_provider import (
    PaymobProvider,
    auth_token as paymob_auth_token,
    register_order as paymob_register_order,
    create_payment_key as paymob_create_payment_key,
    verify_callback_hmac as paymob_verify_callback_hmac,
    get_integration_id as paymob_get_integration_id,
)

from services.payment_platform.providers.fawry_provider import (
    FawryProvider,
    create_charge as fawry_create_charge,
    verify_webhook as fawry_verify_webhook,
    refund as fawry_refund,
    get_charge_status as fawry_get_charge_status,
)

from services.payment_platform.providers.valu_provider import (
    ValuProvider,
    create_charge as valu_create_charge,
    check_eligibility as valu_check_eligibility,
)

from services.payment_platform.providers.egypt_bnpl_providers import (
    AmanProvider,
    ContactProvider,
    SymplProvider,
    get_bnpl_provider,
    list_available_bnpl_providers,
)

__all__ = [
    # Base
    "BaseIntegration",
    "PaymentProviderError",
    "egp_to_piastres",
    "piastres_to_egp",
    # Paymob
    "PaymobProvider",
    "paymob_auth_token",
    "paymob_register_order",
    "paymob_create_payment_key",
    "paymob_verify_callback_hmac",
    "paymob_get_integration_id",
    # Fawry
    "FawryProvider",
    "fawry_create_charge",
    "fawry_verify_webhook",
    "fawry_refund",
    "fawry_get_charge_status",
    # Valu BNPL
    "ValuProvider",
    "valu_create_charge",
    "valu_check_eligibility",
    # Other Egypt BNPL
    "AmanProvider",
    "ContactProvider",
    "SymplProvider",
    "get_bnpl_provider",
    "list_available_bnpl_providers",
]
