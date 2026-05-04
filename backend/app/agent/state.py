from typing import Annotated, Literal, TypedDict
import operator
from langchain_core.messages import BaseMessage


class UserProfile(TypedDict, total=False):
    onboarding_complete: bool
    goal: str | None
    deadline: str | None
    learning_style: str | None
    sources: list[str]


class SynapseState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    user_id: str
    profile: UserProfile
    route: Literal["onboarding", "session"]
