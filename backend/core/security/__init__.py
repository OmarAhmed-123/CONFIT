# Security Module
# Phase 8: Security Hardening exports

try:
    from core.security.password_handler import password_handler, PasswordHandler
except ImportError:
    pass

try:
    from core.security.rbac import Permission, require_role, require_permission
except ImportError:
    pass

try:
    from core.security.jwt_handler import JWTHandler
except ImportError:
    pass

try:
    from core.security.token_blacklist import TokenBlacklist
except ImportError:
    pass

try:
    from core.security.secrets_manager import SecretsManager
except ImportError:
    pass

try:
    from core.security.secret_bootstrap import bootstrap_secrets
except ImportError:
    pass

try:
    from core.security.input_sanitization import InputSanitizer
except ImportError:
    pass

# Phase 8 additions
try:
    from core.security.mfa import (
        HAS_MFA,
        is_mfa_required,
        generate_totp_secret,
        verify_totp,
        generate_provisioning_uri,
        generate_qr_code_base64,
        generate_backup_codes,
    )
except ImportError:
    pass

try:
    from core.security.brute_force import (
        BruteForceProtector,
        brute_force_protector,
        init_brute_force_protector,
        MAX_FAILED_ATTEMPTS,
        LOCKOUT_DURATION_SECONDS,
    )
except ImportError:
    pass

try:
    from core.security.audit_log import (
        AuditEventType,
        AuditOutcome,
        AuditLogger,
        audit_logger,
        audit_context_from_request,
    )
except ImportError:
    pass

try:
    from core.security.xss_sanitizer import sanitize_html, strip_all_html
except ImportError:
    pass

try:
    from core.security.ssrf_guard import is_url_safe, validate_outbound_url
except ImportError:
    pass
