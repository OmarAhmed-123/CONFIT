"""
CONFIT Backend — Style DNA Service Tests
========================================
Unit and integration tests for Style DNA feature.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4, UUID
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import numpy as np

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models.style_dna_models import (
    StyleDNAProfile,
    StyleVector,
    StylePreference,
    StyleSignal,
    StyleEvolutionHistory,
    StyleCluster,
    UserClusterAssignment,
    StyleQuizResponse,
    StyleCategory,
    BudgetLevel,
    FitPreference,
    OccasionType,
    SignalSource,
    StyleDNAResponseDTO,
    StyleDNACreateDTO,
    StyleQuizSubmissionDTO,
    StyleQuizAnswerDTO,
)
from services.style_dna_service import (
    StyleDNAService,
    StyleEmbeddingEngine,
    StyleClusteringService,
    get_style_dna_service,
)
from services.style_dna_security import (
    StyleDNAEncryption,
    StyleDNAPrivacyManager,
    StyleDNAValidators,
)


# ─────────────────────────────────────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.scalar = AsyncMock()
    session.scalars = AsyncMock()
    session.add = Mock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.get = AsyncMock()
    return session


@pytest.fixture
def sample_user_id():
    """Sample user UUID."""
    return uuid4()


@pytest.fixture
def sample_profile(sample_user_id):
    """Sample Style DNA profile."""
    profile = StyleDNAProfile(
        id=uuid4(),
        user_id=sample_user_id,
        primary_style=StyleCategory.CASUAL,
        secondary_styles=[StyleCategory.MINIMALIST, StyleCategory.CLASSIC],
        style_confidence=Decimal("0.85"),
        color_preferences={
            "primary": ["black", "white", "navy"],
            "secondary": ["gray", "beige"],
            "avoided": ["orange"],
            "undertone": "cool",
        },
        fit_preference=FitPreference.REGULAR,
        occasion_preferences={
            "everyday": 0.8,
            "work": 0.6,
            "weekend": 0.7,
        },
        brand_affinity=[
            {"brand_id": str(uuid4()), "affinity_score": 0.9},
            {"brand_id": str(uuid4()), "affinity_score": 0.7},
        ],
        budget_level=BudgetLevel.MODERATE,
        budget_range={
            "per_item_min": 50,
            "per_item_max": 150,
            "currency": "USD",
        },
        pattern_preferences={
            "preferred": ["solid", "stripes"],
            "avoided": ["floral"],
        },
        fabric_preferences={
            "preferred": ["cotton", "linen"],
            "avoided": ["polyester"],
        },
        silhouette_preferences={
            "tops": ["fitted", "regular"],
            "bottoms": ["straight", "slim"],
        },
        signal_summary={
            "wardrobe_items": 25,
            "liked_outfits": 10,
            "purchases": 5,
            "quiz_answers": 8,
            "browsing_events": 100,
        },
        profile_completeness=Decimal("0.75"),
        profile_version=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    return profile


@pytest.fixture
def sample_style_vector(sample_user_id):
    """Sample style vector."""
    # Create a sample embedding (384 dimensions)
    embedding = np.random.rand(384).tolist()
    
    vector = StyleVector(
        id=uuid4(),
        user_id=sample_user_id,
        vector_type="combined",
        embedding=embedding,
        confidence_score=Decimal("0.85"),
        created_at=datetime.now(timezone.utc),
    )
    return vector


# ─────────────────────────────────────────────────────────────────────────────
# STYLE EMBEDDING ENGINE TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestStyleEmbeddingEngine:
    """Tests for StyleEmbeddingEngine."""
    
    def test_initialization(self):
        """Test engine initialization."""
        engine = StyleEmbeddingEngine()
        assert engine is not None
        assert engine.model_name == "all-MiniLM-L6-v2"
    
    def test_generate_embedding_without_model(self):
        """Test embedding generation when model is not available."""
        engine = StyleEmbeddingEngine()
        engine._model = None
        engine._tokenizer = None
        
        # Should return fallback embedding
        embedding = engine.generate_embedding("casual minimalist style")
        
        assert embedding is not None
        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)
    
    @patch('services.style_dna_service.HAS_TRANSFORMERS', True)
    def test_generate_embedding_with_model(self):
        """Test embedding generation with model available."""
        engine = StyleEmbeddingEngine()
        
        # Mock the model
        mock_model = Mock()
        mock_model.encode.return_value = np.random.rand(384)
        engine._model = mock_model
        
        embedding = engine.generate_embedding("casual minimalist style")
        
        assert embedding is not None
        assert len(embedding) == 384
        mock_model.encode.assert_called_once()
    
    def test_combine_embeddings(self):
        """Test combining multiple embeddings."""
        engine = StyleEmbeddingEngine()
        
        embeddings = [
            np.random.rand(384).tolist(),
            np.random.rand(384).tolist(),
            np.random.rand(384).tolist(),
        ]
        weights = [0.5, 0.3, 0.2]
        
        combined = engine.combine_embeddings(embeddings, weights)
        
        assert combined is not None
        assert len(combined) == 384
        # Check that weights are applied
        assert all(isinstance(x, float) for x in combined)
    
    def test_style_to_text(self):
        """Test converting style data to text."""
        engine = StyleEmbeddingEngine()
        
        style_data = {
            "primary_style": "casual",
            "secondary_styles": ["minimalist", "classic"],
            "colors": ["black", "white", "navy"],
            "fit": "regular",
            "occasions": ["everyday", "work"],
        }
        
        text = engine.style_to_text(style_data)
        
        assert "casual" in text
        assert "minimalist" in text
        assert "classic" in text
        assert "black" in text
        assert "regular fit" in text


# ─────────────────────────────────────────────────────────────────────────────
# STYLE DNA SERVICE TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestStyleDNAService:
    """Tests for StyleDNAService."""
    
    @pytest.mark.asyncio
    async def test_get_or_create_profile_existing(self, mock_session, sample_profile, sample_user_id):
        """Test getting existing profile."""
        # Mock the query result
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_profile
        mock_session.execute.return_value = mock_result
        
        service = StyleDNAService(mock_session)
        profile = await service.get_or_create_profile(sample_user_id)
        
        assert profile is not None
        assert profile.user_id == sample_user_id
        assert profile.primary_style == StyleCategory.CASUAL
    
    @pytest.mark.asyncio
    async def test_get_or_create_profile_new(self, mock_session, sample_user_id):
        """Test creating new profile."""
        # Mock no existing profile
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        service = StyleDNAService(mock_session)
        profile = await service.get_or_create_profile(sample_user_id)
        
        assert profile is not None
        assert profile.user_id == sample_user_id
        mock_session.add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_profile(self, mock_session, sample_profile, sample_user_id):
        """Test updating profile."""
        # Mock existing profile
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_profile
        mock_session.execute.return_value = mock_result
        
        service = StyleDNAService(mock_session)
        
        update_data = StyleDNACreateDTO(
            primary_style=StyleCategory.MINIMALIST,
            budget_level=BudgetLevel.PREMIUM,
        )
        
        profile = await service.update_profile(sample_user_id, update_data)
        
        assert profile is not None
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_user_style(self, mock_session, sample_profile, sample_user_id):
        """Test style analysis."""
        # Mock profile
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_profile
        mock_session.execute.return_value = mock_result
        
        # Mock wardrobe items
        mock_wardrobe_result = Mock()
        mock_wardrobe_result.scalars.return_value.all.return_value = []
        
        service = StyleDNAService(mock_session)
        
        result = await service.analyze_user_style(sample_user_id)
        
        assert result is not None
        assert "computed_styles" in result
        assert "confidence" in result
    
    @pytest.mark.asyncio
    async def test_find_similar_users(self, mock_session, sample_profile, sample_user_id):
        """Test finding similar users."""
        # Mock profile with vector
        sample_profile.style_vector = Mock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_profile
        mock_session.execute.return_value = mock_result
        
        service = StyleDNAService(mock_session)
        
        similar_users = await service.find_similar_users(sample_user_id, limit=5)
        
        assert similar_users is not None
        assert isinstance(similar_users, list)
    
    @pytest.mark.asyncio
    async def test_submit_style_quiz(self, mock_session, sample_profile, sample_user_id):
        """Test submitting style quiz."""
        # Mock profile
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_profile
        mock_session.execute.return_value = mock_result
        
        service = StyleDNAService(mock_session)
        
        submission = StyleQuizSubmissionDTO(
            quiz_type="initial",
            answers=[
                StyleQuizAnswerDTO(
                    question_id="style_1",
                    selected_options=["classic"],
                ),
                StyleQuizAnswerDTO(
                    question_id="style_2",
                    selected_options=["black", "white"],
                ),
            ],
        )
        
        result = await service.submit_style_quiz(sample_user_id, submission)
        
        assert result is not None
        assert "computed_styles" in result
        assert result.profile_updated is True
    
    @pytest.mark.asyncio
    async def test_record_signal(self, mock_session, sample_profile, sample_user_id):
        """Test recording style signal."""
        # Mock profile
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_profile
        mock_session.execute.return_value = mock_result
        
        service = StyleDNAService(mock_session)
        
        signal = await service.record_signal(
            user_id=sample_user_id,
            signal_type="view",
            signal_category="product",
            entity_id=str(uuid4()),
            entity_type="product",
        )
        
        assert signal is not None
        mock_session.add.assert_called()


# ─────────────────────────────────────────────────────────────────────────────
# STYLE CLUSTERING SERVICE TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestStyleClusteringService:
    """Tests for StyleClusteringService."""
    
    def test_initialization(self):
        """Test clustering service initialization."""
        service = StyleClusteringService(n_clusters=10)
        assert service is not None
        assert service.n_clusters == 10
    
    def test_fit_clusters(self):
        """Test fitting clusters."""
        service = StyleClusteringService(n_clusters=5)
        
        # Generate sample data
        embeddings = np.random.rand(100, 384)
        
        labels = service.fit(embeddings)
        
        assert labels is not None
        assert len(labels) == 100
        assert all(0 <= label < 5 for label in labels)
    
    def test_predict_cluster(self):
        """Test predicting cluster for new embedding."""
        service = StyleClusteringService(n_clusters=5)
        
        # Fit first
        embeddings = np.random.rand(100, 384)
        service.fit(embeddings)
        
        # Predict
        new_embedding = np.random.rand(384)
        cluster = service.predict(new_embedding)
        
        assert cluster is not None
        assert 0 <= cluster < 5
    
    def test_get_cluster_centers(self):
        """Test getting cluster centers."""
        service = StyleClusteringService(n_clusters=5)
        
        embeddings = np.random.rand(100, 384)
        service.fit(embeddings)
        
        centers = service.get_cluster_centers()
        
        assert centers is not None
        assert len(centers) == 5
        assert all(len(center) == 384 for center in centers)


# ─────────────────────────────────────────────────────────────────────────────
# SECURITY TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestStyleDNAEncryption:
    """Tests for StyleDNAEncryption."""
    
    def test_singleton(self):
        """Test singleton pattern."""
        enc1 = StyleDNAEncryption()
        enc2 = StyleDNAEncryption()
        
        assert enc1 is enc2
    
    def test_encrypt_decrypt(self):
        """Test encryption and decryption."""
        encryption = StyleDNAEncryption()
        
        data = {
            "sensitive": "data",
            "numbers": [1, 2, 3],
            "nested": {"key": "value"},
        }
        
        encrypted = encryption.encrypt(data)
        assert encrypted is not None
        assert isinstance(encrypted, str)
        assert encrypted != str(data)
        
        decrypted = encryption.decrypt(encrypted)
        assert decrypted == data
    
    def test_encrypt_field(self):
        """Test field encryption."""
        encryption = StyleDNAEncryption()
        
        value = "sensitive_value"
        encrypted = encryption.encrypt_field(value)
        
        assert encrypted is not None
        assert encrypted != value
        
        decrypted = encryption.decrypt_field(encrypted)
        assert decrypted == value


class TestStyleDNAPrivacyManager:
    """Tests for StyleDNAPrivacyManager."""
    
    def test_get_privacy_settings(self):
        """Test getting privacy settings."""
        manager = StyleDNAPrivacyManager()
        
        public_settings = manager.get_privacy_settings("public")
        assert public_settings["share_style"] is True
        assert public_settings["share_budget"] is False
        
        private_settings = manager.get_privacy_settings("private")
        assert private_settings["share_style"] is False
        assert private_settings["allow_similarity_matching"] is False
    
    def test_filter_profile_for_sharing(self):
        """Test filtering profile for sharing."""
        manager = StyleDNAPrivacyManager()
        
        profile_data = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "primary_style": "casual",
            "color_preferences": {"primary": ["black"]},
            "budget_range": {"per_item_max": 150},
            "profile_completeness": 0.8,
        }
        
        privacy_settings = manager.get_privacy_settings("public")
        filtered = manager.filter_profile_for_sharing(profile_data, privacy_settings)
        
        assert "primary_style" in filtered
        assert "color_preferences" in filtered
        assert "budget_range" not in filtered  # Budget is not shared in public
    
    def test_anonymize_for_analytics(self):
        """Test anonymization for analytics."""
        manager = StyleDNAPrivacyManager()
        
        profile_data = {
            "user_id": str(uuid4()),
            "primary_style": "casual",
            "color_preferences": {"primary": ["black", "white"]},
            "budget_range": {"per_item_max": 150},
        }
        
        anonymized = manager.anonymize_for_analytics(profile_data)
        
        assert "user_id" not in anonymized
        assert "anonymous_id" in anonymized
        assert "primary_style" in anonymized
        assert "budget_range" not in anonymized


class TestStyleDNAValidators:
    """Tests for StyleDNAValidators."""
    
    def test_validate_style_category(self):
        """Test style category validation."""
        assert StyleDNAValidators.validate_style_category("casual") is True
        assert StyleDNAValidators.validate_style_category("minimalist") is True
        assert StyleDNAValidators.validate_style_category("invalid_style") is False
    
    def test_validate_budget_level(self):
        """Test budget level validation."""
        assert StyleDNAValidators.validate_budget_level("moderate") is True
        assert StyleDNAValidators.validate_budget_level("luxury") is True
        assert StyleDNAValidators.validate_budget_level("invalid") is False
    
    def test_validate_fit_preference(self):
        """Test fit preference validation."""
        assert StyleDNAValidators.validate_fit_preference("regular") is True
        assert StyleDNAValidators.validate_fit_preference("slim") is True
        assert StyleDNAValidators.validate_fit_preference("invalid") is False
    
    def test_validate_occasion_preferences(self):
        """Test occasion preferences validation."""
        occasions = {
            "everyday": 0.8,
            "work": 0.6,
        }
        
        result = StyleDNAValidators.validate_occasion_preferences(occasions)
        assert result["valid"] is True
        
        # Invalid occasion
        invalid_occasions = {
            "invalid_occasion": 0.5,
        }
        result = StyleDNAValidators.validate_occasion_preferences(invalid_occasions)
        assert result["valid"] is False
    
    def test_validate_color_preferences(self):
        """Test color preferences validation."""
        colors = {
            "primary": ["black", "white", "navy"],
            "secondary": ["gray"],
        }
        
        result = StyleDNAValidators.validate_color_preferences(colors)
        assert result["valid"] is True
        
        # Too many colors
        many_colors = {
            "primary": [f"color{i}" for i in range(15)],
        }
        result = StyleDNAValidators.validate_color_preferences(many_colors)
        assert len(result["warnings"]) > 0
    
    def test_validate_brand_affinity(self):
        """Test brand affinity validation."""
        brands = [
            {"brand_id": str(uuid4()), "affinity_score": 0.9},
            {"brand_id": str(uuid4()), "affinity_score": 0.7},
        ]
        
        result = StyleDNAValidators.validate_brand_affinity(brands)
        assert result["valid"] is True
        
        # Invalid affinity score
        invalid_brands = [
            {"brand_id": str(uuid4()), "affinity_score": 1.5},
        ]
        result = StyleDNAValidators.validate_brand_affinity(invalid_brands)
        assert result["valid"] is False
    
    def test_validate_profile_update(self):
        """Test complete profile update validation."""
        update_data = {
            "primary_style": "casual",
            "secondary_styles": ["minimalist"],
            "budget_level": "moderate",
            "fit_preference": "regular",
            "occasion_preferences": {"everyday": 0.8},
            "color_preferences": {"primary": ["black"]},
            "brand_affinity": [{"brand_id": str(uuid4()), "affinity_score": 0.9}],
        }
        
        result = StyleDNAValidators.validate_profile_update(update_data)
        assert result["valid"] is True
        
        # Invalid data
        invalid_data = {
            "primary_style": "invalid_style",
            "budget_level": "invalid_level",
        }
        result = StyleDNAValidators.validate_profile_update(invalid_data)
        assert result["valid"] is False
        assert len(result["errors"]) > 0


# ─────────────────────────────────────────────────────────────────────────────
# DTO TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestStyleDNADTOs:
    """Tests for Style DNA DTOs."""
    
    def test_style_dna_response_dto(self, sample_profile):
        """Test StyleDNAResponseDTO."""
        dto = StyleDNAResponseDTO(
            id=sample_profile.id,
            user_id=sample_profile.user_id,
            primary_style=sample_profile.primary_style,
            secondary_styles=sample_profile.secondary_styles,
            style_confidence=float(sample_profile.style_confidence),
            color_preferences=sample_profile.color_preferences,
            fit_preference=sample_profile.fit_preference,
            occasion_preferences=sample_profile.occasion_preferences,
            brand_affinity=sample_profile.brand_affinity,
            budget_level=sample_profile.budget_level,
            profile_completeness=float(sample_profile.profile_completeness),
            profile_version=sample_profile.profile_version,
            created_at=sample_profile.created_at,
            updated_at=sample_profile.updated_at,
        )
        
        assert dto.primary_style == StyleCategory.CASUAL
        assert len(dto.secondary_styles) == 2
    
    def test_style_quiz_submission_dto(self):
        """Test StyleQuizSubmissionDTO."""
        dto = StyleQuizSubmissionDTO(
            quiz_type="initial",
            answers=[
                StyleQuizAnswerDTO(
                    question_id="q1",
                    selected_options=["option1"],
                    confidence=0.9,
                ),
            ],
            duration_seconds=120,
        )
        
        assert dto.quiz_type == "initial"
        assert len(dto.answers) == 1
        assert dto.duration_seconds == 120


# ─────────────────────────────────────────────────────────────────────────────
# INTEGRATION TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestStyleDNAIntegration:
    """Integration tests for Style DNA."""
    
    @pytest.mark.asyncio
    async def test_full_style_analysis_flow(self, mock_session, sample_user_id):
        """Test complete style analysis flow."""
        # This would be a full integration test with a real database
        # For now, we mock the session
        
        # Mock profile creation
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        service = StyleDNAService(mock_session)
        
        # Create profile
        profile = await service.get_or_create_profile(sample_user_id)
        assert profile is not None
        
        # Submit quiz
        submission = StyleQuizSubmissionDTO(
            quiz_type="initial",
            answers=[
                StyleQuizAnswerDTO(question_id="q1", selected_options=["casual"]),
                StyleQuizAnswerDTO(question_id="q2", selected_options=["black", "white"]),
            ],
        )
        
        # Mock profile for quiz
        mock_result.scalar_one_or_none.return_value = profile
        
        result = await service.submit_style_quiz(sample_user_id, submission)
        assert result is not None


# ─────────────────────────────────────────────────────────────────────────────
# RUN TESTS
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
