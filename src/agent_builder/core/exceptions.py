"""Custom exceptions for Agent Team Builder."""


class AgentBuilderError(Exception):
    """Base error for the agent system."""


class StateTransitionError(AgentBuilderError):
    """Invalid orchestrator state transition."""


class WorkspaceError(AgentBuilderError):
    """Workspace I/O or path error."""


class StateNotFoundError(WorkspaceError):
    """No persisted session state in workspace."""
