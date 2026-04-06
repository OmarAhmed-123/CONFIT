"""
CONFIT Virtual Try-On subpackage (pose, segmentation, neural engines).

Do not import heavy modules here — importing `services.tryon.*` submodules must not
execute optional GPU stacks. Import explicitly, e.g.:
  from services.tryon.orchestrator import TryOnOrchestrator
"""
