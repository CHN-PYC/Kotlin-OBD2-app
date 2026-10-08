from app.services.retrieval.query_retrieval import QueryRetrievalService
from app.tools.registry import ToolRegistry
from app.tools.vehicle import (
    AnalyzeSessionSignalsTool,
    InterpretDtcTool,
    LookupPidDefinitionTool,
    SearchVehicleKnowledgeTool,
)


def create_vehicle_tool_registry(retrieval_service: QueryRetrievalService) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(SearchVehicleKnowledgeTool(retrieval_service))
    registry.register(LookupPidDefinitionTool())
    registry.register(InterpretDtcTool())
    registry.register(AnalyzeSessionSignalsTool())
    return registry
