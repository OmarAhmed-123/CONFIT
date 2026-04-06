"""
CONFIT Backend — Authentication Service
=========================================
JWT-based authentication with bcrypt password hashing.
Persists users in the database; use get_auth_service(db) via FastAPI Depends.
"""

import os
import secrets
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
import bcrypt
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.models import User as UserModel
from sqlalchemy.exc import IntegrityError
from core.security.secret_bootstrap import bootstrap_secret

logger = logging.getLogger(__name__)

# Stable guest row for anonymous flows (must match any FK expectations)
GUEST_USER_ID = "00000000-0000-4000-8000-000000000001"
GUEST_EMAIL = "guest@confit.com"

# ── Configuration ──────────────────────────────────────────────────

def _load_jwt_secret() -> str:
    """Load JWT secret from environment. Raises RuntimeError on missing config."""
    # In local dev we bootstrap once and persist, so JWT remains stable across restarts.
    return bootstrap_secret(
        "JWT_SECRET",
        min_length=32,
        placeholder_contains=(
            "change-me",
            "change_me_to_a_random_secret",
            "CHANGE_ME_TO_A_RANDOM_SECRET",
            "default",
            "secret",
            "password",
            "jwt-secret",
        ),
    )


JWT_SECRET = _load_jwt_secret()
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24


# ── Pydantic models (API contract) ──────────────────────────────────

class UserProfile(BaseModel):
    """Public user profile (never includes password)."""

    id: str  # Keep as str for API compatibility, but it's UUID
    name: str
    email: str
    created_at: str

    phone: Optional[str] = None
    address: Optional[dict] = None
    avatar_url: Optional[str] = None
    date_of_birth: Optional[str] = None  # ISO format for birthday emails

    style_preference: Optional[str] = None
    body_profile: Optional[dict] = None
    budget_range: Optional[dict] = None
    preferred_brands: Optional[list[str]] = None
    occasion_preferences: Optional[list[str]] = None

    marketing_consent: Optional[bool] = None
    data_sharing_consent: Optional[bool] = None
    roles: list[str] = Field(default_factory=list)


# ── Service ────────────────────────────────────────────────────────

class AuthService:
    """Handles user registration, login, and JWT using the database."""

    def __init__(self, db: Session):
        # Never seed here — seed_auth_users() runs once at app startup to avoid
        # SQLite races (UNIQUE failures) and ORM errors under concurrent requests.
        self._db = db

    @staticmethod
    def _hash_password(password: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    @staticmethod
    def _verify_password(password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

    @staticmethod
    def create_token(user_id: str, email: str) -> str:
        payload = {
            "sub": str(user_id),
            "email": email,
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
            "iat": datetime.now(timezone.utc),
            "iss": "confit",
            "jti": secrets.token_hex(16),
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    @staticmethod
    def create_refresh_token(user_id: str, email: str) -> str:
        payload = {
            "sub": str(user_id),
            "email": email,
            "type": "refresh",
            "exp": datetime.now(timezone.utc) + timedelta(days=7),
            "iat": datetime.now(timezone.utc),
            "iss": "confit",
            "jti": secrets.token_hex(16),
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        try:
            return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid token")
            return None

    def _user_to_profile(self, row: UserModel) -> UserProfile:
        created = row.created_at.isoformat() if row.created_at else ""
        dob = row.date_of_birth.isoformat() if row.date_of_birth else None
        from database.models import UserRole
        role_rows = self._db.query(UserRole).filter(UserRole.user_id == row.id).all()
        roles = [str(r.role.value if hasattr(r.role, "value") else r.role) for r in role_rows] or ["user"]
        return UserProfile(
            id=str(row.id),
            name=row.name,
            email=row.email,
            created_at=created,
            phone=row.phone,
            address=row.address,
            avatar_url=row.avatar_url,
            date_of_birth=dob,
            style_preference=row.style_preference,
            body_profile=row.body_profile,
            budget_range=row.budget_range,
            preferred_brands=row.preferred_brands,
            occasion_preferences=row.occasion_preferences,
            marketing_consent=row.marketing_consent,
            data_sharing_consent=row.data_sharing_consent,
            roles=roles,
        )

    def register(
        self,
        name: str,
        email: str,
        password: str,
        *,
        date_of_birth: Optional[datetime] = None,
        phone: Optional[str] = None,
        address: Optional[dict] = None,
        style_preference: Optional[str] = None,
        body_profile: Optional[dict] = None,
        budget_range: Optional[dict] = None,
        preferred_brands: Optional[list[str]] = None,
        occasion_preferences: Optional[list[str]] = None,
        marketing_consent: Optional[bool] = None,
        data_sharing_consent: Optional[bool] = None,
        user_type: str = "shopper",
        # Brand partner fields
        brand_name: Optional[str] = None,
        brand_description: Optional[str] = None,
        brand_website: Optional[str] = None,
        brand_logo_url: Optional[str] = None,
        # Stylist fields
        stylist_bio: Optional[str] = None,
        stylist_specialties: Optional[list[str]] = None,
        stylist_portfolio_url: Optional[str] = None,
        stylist_experience_years: Optional[int] = None,
    ) -> tuple[Optional[UserProfile], Optional[str]]:
        """Register a new user. Returns (profile, error_message).
        
        user_type determines the role assigned:
        - shopper -> AppRole.user
        - brand_partner -> AppRole.brand_manager
        - stylist -> AppRole.stylist
        - admin -> AppRole.admin (requires admin approval in production)
        """
        email_lower = email.lower().strip()

        if self._db.query(UserModel).filter(UserModel.email == email_lower).first():
            return None, "An account with this email already exists."

        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        row = UserModel(
            id=user_id,
            name=name.strip(),
            email=email_lower,
            password_hash=self._hash_password(password),
            created_at=now,
            phone=phone,
            address=address,
            date_of_birth=date_of_birth,
            style_preference=style_preference,
            body_profile=body_profile,
            budget_range=budget_range,
            preferred_brands=preferred_brands,
            occasion_preferences=occasion_preferences,
            marketing_consent=marketing_consent,
            data_sharing_consent=data_sharing_consent,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)

        # Create user_roles based on user_type
        from database.models import UserRole, UserGamification, AppRole, Brand
        
        # Map user_type to AppRole
        role_mapping = {
            "shopper": AppRole.user,
            "brand_partner": AppRole.brand_manager,
            "stylist": AppRole.stylist,
            "admin": AppRole.admin,
        }
        assigned_role = role_mapping.get(user_type, AppRole.user)
        
        user_role = UserRole(
            user_id=row.id,
            role=assigned_role,
        )
        self._db.add(user_role)

        # Create user_gamification
        gamification = UserGamification(
            user_id=row.id,
        )
        self._db.add(gamification)

        # Handle role-specific data
        if user_type == "brand_partner" and brand_name:
            # Create brand for brand partner
            brand_id = f"brand-{str(uuid.uuid4())[:8]}"
            new_brand = Brand(
                id=brand_id,
                name=brand_name,
                description=brand_description or "",
                website=brand_website,
                logo_url=brand_logo_url,
            )
            self._db.add(new_brand)
            
            # Create brand manager association
            try:
                from models.production_models import BrandManager as BrandManagerModel
                brand_manager = BrandManagerModel(
                    brand_id=brand_id,
                    user_id=row.id,
                    role="owner",
                    is_active=True,
                )
                self._db.add(brand_manager)
            except ImportError:
                logger.warning("BrandManager model not available for brand partner registration")

        # Store stylist-specific data in user profile
        if user_type == "stylist":
            stylist_data = {
                "bio": stylist_bio,
                "specialties": stylist_specialties or [],
                "portfolio_url": stylist_portfolio_url,
                "experience_years": stylist_experience_years or 0,
            }
            # Store in body_profile as stylist_profile for now
            # In production, you'd add a dedicated stylist_profile column
            row.body_profile = {"stylist_profile": stylist_data}

        self._db.commit()

        return self._user_to_profile(row), None

    def login(self, email: str, password: str) -> tuple[Optional[UserProfile], Optional[str], Optional[str], Optional[str]]:
        """Authenticate user. Returns (profile, access_token, refresh_token, error_message)."""
        email_lower = email.lower().strip()
        row = self._db.query(UserModel).filter(UserModel.email == email_lower).first()

        if not row or not self._verify_password(password, row.password_hash):
            return None, None, None, "Invalid email or password."

        access_token = self.create_token(row.id, row.email)
        refresh_token = self.create_refresh_token(row.id, row.email)
        return self._user_to_profile(row), access_token, refresh_token, None

    def get_user_by_email(self, email: str) -> Optional[UserProfile]:
        row = self._db.query(UserModel).filter(UserModel.email == email.lower().strip()).first()
        return self._user_to_profile(row) if row else None

    def get_user_by_token(self, token: str) -> Optional[UserProfile]:
        payload = self.decode_token(token)
        if not payload:
            return None
        return self.get_user_by_email(payload.get("email", ""))

    def refresh_tokens(self, token: str) -> Optional[tuple[str, str]]:
        """
        Issue new access + refresh JWTs from a valid refresh token.
        Rejects access tokens to prevent token type confusion.
        """
        try:
            payload = jwt.decode(
                token,
                JWT_SECRET,
                algorithms=[JWT_ALGORITHM],
                options={"verify_exp": True},
            )
        except jwt.InvalidTokenError:
            return None
        if payload.get("type") != "refresh":
            return None
        email = payload.get("email")
        if not email:
            return None
        profile = self.get_user_by_email(str(email))
        if not profile:
            return None
        new_access = self.create_token(profile.id, profile.email)
        new_refresh = self.create_refresh_token(profile.id, profile.email)
        return new_access, new_refresh

    def get_user_by_id(self, user_id: str) -> Optional[UserProfile]:
        row = self._db.query(UserModel).filter(UserModel.id == user_id).first()
        return self._user_to_profile(row) if row else None

    def update_user(self, email: str, updates: dict) -> Optional[UserProfile]:
        row = self._db.query(UserModel).filter(UserModel.email == email.lower().strip()).first()
        if not row:
            return None

        allowed = {
            "name", "phone", "address", "style_preference", "avatar_url",
            "body_profile", "budget_range", "preferred_brands", "occasion_preferences",
            "marketing_consent", "data_sharing_consent",
        }
        for key, value in updates.items():
            if key in allowed and value is not None:
                setattr(row, key, value)

        self._db.commit()
        self._db.refresh(row)
        return self._user_to_profile(row)


def seed_auth_users(db: Session) -> None:
    """
    Idempotent user seeding — call once at application startup only.

    Running this on every HTTP request caused SQLite races (UNIQUE on users.email),
    IntegrityError on guest insert, and sporadic ORM IndexError under load.
    """
    import string

    auth = AuthService(db)

    env = os.getenv("ENV", "development")
    if env == "development" and db.query(UserModel).filter(UserModel.email == "demo@confit.com").first() is None:
        demo_password = os.getenv("DEMO_PASSWORD")
        if not demo_password:
            demo_password = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
            logger.warning(
                "DEMO_PASSWORD not set. Generated random dev password. Set DEMO_PASSWORD in .env for stable login."
            )
        _profile, err = auth.register(
            name="Demo User",
            email="demo@confit.com",
            password=demo_password,
        )
        if err:
            logger.warning("Demo user not seeded: %s", err)
        else:
            logger.info("Demo user seeded: demo@confit.com")

    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    if admin_email and admin_password:
        admin_email = admin_email.lower().strip()
        if db.query(UserModel).filter(UserModel.email == admin_email).first() is None:
            _p, err = auth.register(
                name="Admin",
                email=admin_email,
                password=admin_password,
            )
            if err:
                logger.warning("Admin user not seeded: %s", err)
            else:
                logger.info("Admin user seeded: %s", admin_email)
    elif admin_email or admin_password:
        logger.warning("Both ADMIN_EMAIL and ADMIN_PASSWORD must be set to seed admin.")

    if db.query(UserModel).filter(UserModel.email == GUEST_EMAIL).first() is not None:
        guest_exists = True
    else:
        guest_exists = False

    if not guest_exists:
        guest_pw = secrets.token_urlsafe(16)
        guest = UserModel(
            id=GUEST_USER_ID,
            name="Guest",
            email=GUEST_EMAIL,
            password_hash=auth._hash_password(guest_pw),
            created_at=datetime.now(timezone.utc),
        )
        db.add(guest)
        try:
            db.commit()
            logger.info("Guest user seeded for anonymous orders (%s)", GUEST_EMAIL)
        except IntegrityError:
            db.rollback()
            logger.debug("Guest user already present (IntegrityError).")

    # ── Seed role assignments & brand managers (dev convenience) ──
    # Pickup notifications require:
    # - UserRole.role in (brand_manager, admin) for owner-only API access
    # - BrandManager rows for the store brand to choose receiver_id
    try:
        from database.models import Store as StoreModel, UserRole, AppRole
        from models.production_models import BrandManager as BrandManagerModel

        demo_user = db.query(UserModel).filter(UserModel.email == "demo@confit.com").first()
        admin_user = db.query(UserModel).filter(UserModel.email == "admin@confit.com").first()
        if not demo_user and not admin_user:
            return

        owner_user = admin_user or demo_user

        # Ensure JWT owner access works: update (not insert) to avoid "first()" selecting a stale 'user' role.
        if admin_user:
            for r in db.query(UserRole).filter(UserRole.user_id == admin_user.id).all():
                r.role = AppRole.admin
            if not db.query(UserRole).filter(UserRole.user_id == admin_user.id).first():
                db.add(UserRole(user_id=admin_user.id, role=AppRole.admin))

        if demo_user:
            for r in db.query(UserRole).filter(UserRole.user_id == demo_user.id).all():
                r.role = AppRole.brand_manager
            if not db.query(UserRole).filter(UserRole.user_id == demo_user.id).first():
                db.add(UserRole(user_id=demo_user.id, role=AppRole.brand_manager))

        # BrandManager is unique per (brand_id, user_id). Multiple stores can share the same brand,
        # so seed per distinct brand_id to avoid uniqueness collisions.
        distinct_brand_ids = {s.brand_id for s in db.query(StoreModel).all()}
        for brand_id in distinct_brand_ids:
            existing = (
                db.query(BrandManagerModel)
                .filter(BrandManagerModel.brand_id == brand_id, BrandManagerModel.user_id == owner_user.id)
                .first()
            )
            if not existing:
                db.add(
                    BrandManagerModel(
                        brand_id=brand_id,
                        user_id=owner_user.id,
                        role="owner",
                        is_active=True,
                    )
                )

        db.commit()
        logger.info("Dev seeding: ensured brand managers + owner roles for notifications.")
    except Exception as e:
        db.rollback()
        logger.warning("Dev seeding roles/brand managers skipped: %s", e)
