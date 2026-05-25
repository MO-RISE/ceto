"""Data models for vessel and voyage information."""

from dataclasses import dataclass, field
from typing import List, Optional

from cetos.utils import verify_range, verify_set

# Validation constants
VESSEL_TYPES = [
    "bulk_carrier",
    "chemical_tanker",
    "container",
    "general_cargo",
    "liquified_gas_tanker",
    "oil_tanker",
    "other_liquids_tanker",
    "ferry-pax",
    "cruise",
    "ferry-ropax",
    "refrigerated_cargo",
    "roro",
    "vehicle",
    "yacht",
    "miscellaneous-fishing",
    "service-tug",
    "offshore",
    "service-other",
    "miscellaneous-other",
]

FUEL_TYPES = ["HFO", "MDO", "MeOH", "LNG"]

ENGINE_TYPES = [
    "SSD",
    "MSD",
    "HSD",
    "LNG-Otto-MS",
    "LBSI",
    "gas_turbine",
    "steam_turbine",
]

ENGINE_AGES = ["before_1984", "1984-2000", "after_2000"]

GEAR_TYPES = [
    "seine",
    "troll",
    "gill_net",
    "gill_net_with_power_roller",
    "longline_autoline",
    "longline_sheave_or_drum",
    "longline_sheave_and_drum",
    "pot_large",
    "pot_small",
    "other",
]

REFRIGERATION_SYSTEM_TYPES = ["direct_drive", "electric", "hydraulic"]

# Validation limits
MAX_VESSEL_SPEED_KN = 50
MIN_VESSEL_DRAFT_M = 0.1
MAX_VESSEL_DRAFT_M = 25
MIN_ENGINE_POWER_KW = 5
MAX_ENGINE_POWER_KW = 60_000

MAX_HOURS = 24 * 365  # One year's worth of hours


@dataclass
class VoyageLeg:
    """A single leg of a voyage with distance, speed, and draft."""

    distance_nm: float  # nautical miles
    speed_kn: float  # knots
    draft_m: float  # meters

    def __post_init__(self):
        """Validate voyage leg data."""
        verify_range("distance_nm", self.distance_nm, 0, 50_000)
        verify_range("speed_kn", self.speed_kn, 0.1, MAX_VESSEL_SPEED_KN)
        verify_range("draft_m", self.draft_m, MIN_VESSEL_DRAFT_M, MAX_VESSEL_DRAFT_M)


@dataclass
class VesselData:
    """Vessel specification data."""

    # Physical dimensions
    length_m: float  # meters
    beam_m: float  # meters
    design_speed_kn: float  # knots
    design_draft_m: float  # meters

    # Vessel classification
    type: str  # One of VESSEL_TYPES
    size: Optional[float]  # GT, DWT, or CBM depending on vessel type
    double_ended: bool

    # Propulsion system
    number_of_propulsion_engines: int
    propulsion_engine_power_kw: float  # kilowatts
    propulsion_engine_type: str  # One of ENGINE_TYPES
    propulsion_engine_age: str  # One of ENGINE_AGES
    propulsion_engine_fuel_type: str  # One of FUEL_TYPES

    # Fishing-specific (used by cetos.fishing). Optional so non-fishing
    # vessels keep their existing schema.
    gear_type: Optional[str] = (
        None  # One of GEAR_TYPES; required when type == "miscellaneous-fishing"
    )
    refrigeration_power_kw: Optional[float] = (
        None  # Average installed refrigeration power; None => not installed
    )
    refrigeration_system_type: Optional[str] = (
        None  # One of REFRIGERATION_SYSTEM_TYPES; required iff refrigeration_power_kw is set
    )

    # Planing-hull-specific (used by cetos.planing). Optional so other vessel
    # types keep their existing schema; required by cetos.planing.
    displacement_kg: Optional[float] = (
        None  # Static displacement mass at design_draft_m; required by cetos.planing
    )

    def __post_init__(self):
        """Validate vessel data."""
        verify_range("length_m", self.length_m, 5.0, 450.0)
        verify_range("beam_m", self.beam_m, 1.5, 70.0)
        verify_range("design_speed_kn", self.design_speed_kn, 1.0, MAX_VESSEL_SPEED_KN)
        verify_range(
            "design_draft_m",
            self.design_draft_m,
            MIN_VESSEL_DRAFT_M,
            MAX_VESSEL_DRAFT_M,
        )
        verify_set(
            "number_of_propulsion_engines",
            self.number_of_propulsion_engines,
            [1, 2, 3, 4],
        )
        verify_range(
            "propulsion_engine_power_kw",
            self.propulsion_engine_power_kw,
            MIN_ENGINE_POWER_KW,
            MAX_ENGINE_POWER_KW,
        )
        verify_set("propulsion_engine_type", self.propulsion_engine_type, ENGINE_TYPES)
        verify_set("propulsion_engine_age", self.propulsion_engine_age, ENGINE_AGES)
        verify_set(
            "propulsion_engine_fuel_type", self.propulsion_engine_fuel_type, FUEL_TYPES
        )
        verify_set("type", self.type, VESSEL_TYPES)
        verify_set("double_ended", self.double_ended, [True, False])

        if self.size is not None:
            verify_range("size", self.size, 0, 500_000)

        if self.gear_type is not None:
            verify_set("gear_type", self.gear_type, GEAR_TYPES)
        if self.displacement_kg is not None:
            verify_range("displacement_kg", self.displacement_kg, 100, 1_000_000_000)
        if self.refrigeration_power_kw is not None:
            verify_range("refrigeration_power_kw", self.refrigeration_power_kw, 0, 1000)
            if self.refrigeration_system_type is None:
                raise ValueError(
                    "refrigeration_system_type must be set when refrigeration_power_kw is provided"
                )
            verify_set(
                "refrigeration_system_type",
                self.refrigeration_system_type,
                REFRIGERATION_SYSTEM_TYPES,
            )


@dataclass
class VoyageProfile:
    """Voyage profile describing time and movement patterns."""

    time_anchored_h: float = 0.0  # hours
    time_at_berth_h: float = 0.0  # hours
    legs_manoeuvring: List[VoyageLeg] = field(default_factory=list)
    legs_at_sea: List[VoyageLeg] = field(default_factory=list)
    legs_fishing: List[VoyageLeg] = field(default_factory=list)

    def __post_init__(self):
        """Convert raw tuples to VoyageLeg dataclasses if needed and validate."""

        # Validate time values
        if not isinstance(self.time_anchored_h, (int, float)):
            raise ValueError("time_anchored_h must be a number")
        verify_range("time_anchored_h", self.time_anchored_h, 0, MAX_HOURS)

        if not isinstance(self.time_at_berth_h, (int, float)):
            raise ValueError("time_at_berth_h must be a number")
        verify_range("time_at_berth_h", self.time_at_berth_h, 0, MAX_HOURS)

        # Validate legs are lists
        if not isinstance(self.legs_manoeuvring, list):
            raise ValueError("legs_manoeuvring must be a list")
        if not isinstance(self.legs_at_sea, list):
            raise ValueError("legs_at_sea must be a list")
        if not isinstance(self.legs_fishing, list):
            raise ValueError("legs_fishing must be a list")

        # Convert raw tuples to VoyageLeg dataclasses (validation happens in VoyageLeg)
        self.legs_manoeuvring = [
            VoyageLeg(*leg) if not isinstance(leg, VoyageLeg) else leg
            for leg in self.legs_manoeuvring
        ]
        self.legs_at_sea = [
            VoyageLeg(*leg) if not isinstance(leg, VoyageLeg) else leg
            for leg in self.legs_at_sea
        ]
        self.legs_fishing = [
            VoyageLeg(*leg) if not isinstance(leg, VoyageLeg) else leg
            for leg in self.legs_fishing
        ]
