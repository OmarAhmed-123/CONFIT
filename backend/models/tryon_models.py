"""
CONFIT Backend — Virtual Try-On Data Models
=============================================
Pydantic schemas for virtual try-on and 360-degree
rotation request/response contracts.
"""

from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, field_validator


class TryOnOptions(BaseModel):
    """Optional processing parameters for virtual try-on."""

    fitType: str = Field(
        default="regular",
        description="Garment fit type: tight, regular, or loose",
    )
    qualityThreshold: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
        description="Minimum quality threshold for validation",
    )
    enableValidation: bool = Field(
        default=True,
        description="Whether to run quality validation",
    )
    returnValidationDetails: bool = Field(
        default=False,
        description="Include detailed validation information in response",
    )
    fabricPhysicsEnabled: bool = Field(
        default=True,
        description="Run PBD fabric simulation on classical try-on (pose → physics → blend)",
    )
    fabricLowPower: bool = Field(
        default=False,
        description="Use fewer PBD iterations and a coarser cloth grid on low-power clients",
    )
    # Body DNA — learn once, reuse pose/measurements (classical pipeline)
    userId: Optional[str] = Field(
        default=None,
        description="User id for encrypted Body DNA storage and style memory",
    )
    learnBodyDna: bool = Field(
        default=False,
        description="When True, persist/refine Body DNA after successful pose (measurements only)",
    )
    useStoredBodyDna: bool = Field(
        default=False,
        description="When True, load stored Body DNA and skip pose detection for faster try-on",
    )
    skipPoseDetection: bool = Field(
        default=False,
        description="Force skip MediaPipe pose when body_profile is provided",
    )
    bodyProfileJson: Optional[str] = Field(
        default=None,
        description="Optional inline Body DNA JSON (normalized landmarks); otherwise loaded server-side",
    )
    garmentColorHex: Optional[str] = Field(
        default=None,
        description="Optional garment color for style-memory histograms",
    )
    forceRefreshBodyDna: bool = Field(
        default=False,
        description="When True, overwrite stored Body DNA on next successful analysis",
    )
    noPersistBodyDna: bool = Field(
        default=False,
        description="When True, do not read/write Body DNA storage for this request",
    )
    minOutputQuality: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum composite score to return an image (default: derived from qualityThreshold / TRYON_MIN_OUTPUT_QUALITY)",
    )
    allowLowQualityOutput: bool = Field(
        default=False,
        description="When True, skip minimum-quality rejection (debug only)",
    )

    @field_validator("fitType")
    @classmethod
    def validate_fit_type(cls, value: str) -> str:
        valid_types = {"tight", "regular", "loose"}
        if value.lower() not in valid_types:
            raise ValueError(f"fitType must be one of: {valid_types}")
        return value.lower()


class TryOnRequest(BaseModel):
    """Validated input for a virtual try-on session."""

    userImageBase64: str = Field(
        ...,
        description="Base64-encoded person image (with or without data-URI prefix)",
        min_length=100,
    )
    garmentImageUrl: str = Field(
        ...,
        description="Public URL of the garment image to overlay",
        min_length=5,
    )
    garmentName: str = Field(
        default="garment",
        description="Garment name used for category detection",
        max_length=200,
    )
    garmentCategory: Optional[str] = Field(
        default=None,
        description="Client hint: tops, bottoms, dresses, outerwear, shoes, accessories",
    )
    options: Optional[TryOnOptions] = Field(
        default=None,
        description="Optional processing parameters",
    )

    @field_validator("garmentImageUrl")
    @classmethod
    def validate_url(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("garmentImageUrl must be a valid HTTP or HTTPS URL")
        return value


class QualityMetrics(BaseModel):
    """Quality metrics from validation."""

    overallScore: float = Field(description="Overall quality score (0-1)")
    realismScore: float = Field(description="Realism score (0-1)")
    edgeQualityScore: float = Field(description="Edge quality score (0-1)")
    colorConsistencyScore: float = Field(description="Color consistency score (0-1)")
    proportionScore: float = Field(description="Proportion score (0-1)")
    artifactScore: float = Field(description="Artifact detection score (0-1, higher is better)")
    issues: List[str] = Field(default_factory=list, description="List of detected issues")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")


class TryOnResponse(BaseModel):
    """Standardised output for a virtual try-on session."""

    success: bool
    resultImage: Optional[str] = None
    message: str = ""
    error: Optional[str] = None
    failureKind: Optional[str] = Field(
        default=None,
        description="Machine-readable failure class, e.g. garment_fetch when the garment URL is unreachable",
    )

    # Enhanced response fields
    qualityScore: float = Field(
        default=0.0,
        description="Overall quality score of the result",
    )
    poseDetected: bool = Field(
        default=False,
        description="Whether body pose was successfully detected",
    )
    garmentCategory: str = Field(
        default="tops",
        description="Detected garment category",
    )
    processingTimeMs: float = Field(
        default=0.0,
        description="Processing time in milliseconds",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Non-critical warnings about the result",
    )
    qualityMetrics: Optional[QualityMetrics] = Field(
        default=None,
        description="Detailed quality metrics if validation was performed",
    )
    poseKeypointsJson: Optional[str] = Field(
        default=None,
        description="Optional JSON string of pose landmarks (MediaPipe or silhouette fallback)",
    )
    bodyDnaPoseReused: bool = Field(
        default=False,
        description="True when pose was taken from Body DNA (detection skipped)",
    )
    fitPreviewJson: Optional[str] = Field(
        default=None,
        description="Pre-render fit preview + skeleton (JSON) from Body DNA heuristics",
    )
    bodyProfileJson: Optional[str] = Field(
        default=None,
        description="Newly learned Body DNA profile JSON (measurements only), when applicable",
    )
    qualityDiagnosticsJson: Optional[str] = Field(
        default=None,
        description="Structured quality diagnostics (scores, retries, segmentation source)",
    )
    qualityDiagnostics: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Parsed quality diagnostics object when available",
    )


class RotationRequest(BaseModel):
    """Input for generating 360-degree rotation frames."""

    sourceImageBase64: str = Field(
        ...,
        description="Base64-encoded source image to generate rotation frames from",
        min_length=100,
    )
    frameCount: int = Field(
        default=36,
        ge=8,
        le=72,
        description="Number of rotation frames (8–72, default 36 = 10° steps)",
    )


class RotationResponse(BaseModel):
    """Output containing the generated rotation frames."""

    success: bool
    frames: List[str] = Field(
        default_factory=list,
        description="Array of base64-encoded frame images",
    )
    frameCount: int = 0
    message: str = ""
    error: Optional[str] = None
