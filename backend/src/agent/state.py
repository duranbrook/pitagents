from typing import TypedDict, Optional


class AgentState(TypedDict):
    session_id: str
    audio_url: Optional[str]
    video_url: Optional[str]
    video_frame_urls: list[str]
    labor_rate: float
    pricing_flag: str
    alldata_api_key: Optional[str]
    # Outputs
    transcript: Optional[str]
    findings: Optional[dict]
    vehicle: Optional[dict]
    mileage: Optional[int]
    tire_size: Optional[str]
    damage_notes: list[str]
    estimate: Optional[dict]
    status: str
    error: Optional[str]
