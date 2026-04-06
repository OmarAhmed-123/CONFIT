from api.notification_analytics import CreateABTestRequest, ABTestVariable, ABTestSegment
from services.notification_ml import PipelineConfig, NotificationMLPipeline


def test_notification_ml_exports_available():
    config = PipelineConfig()
    pipeline = NotificationMLPipeline(config=config)
    assert pipeline.config.feature_window_days > 0


def test_ab_test_request_supports_ml_variant_flag():
    request = CreateABTestRequest(
        name="ML timing test",
        hypothesis="ML timing improves opens",
        variable=ABTestVariable.TIMING,
        segment=ABTestSegment.ALL_CUSTOMERS,
        traffic_percentage=50,
        duration_days=14,
        variants=[{"name": "Control"}],
        use_ml_predictions=True,
        ml_confidence_threshold=0.4,
    )
    assert request.use_ml_predictions is True
    assert request.ml_confidence_threshold == 0.4
