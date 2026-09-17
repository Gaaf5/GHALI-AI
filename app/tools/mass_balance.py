from dataclasses import dataclass


@dataclass(frozen=True)
class Stream:
    name: str
    mass: float
    composition: dict[str, float]


def component_mass(stream: Stream, component: str) -> float:
    return stream.mass * stream.composition.get(component, 0.0) / 100.0


def total_mass(streams: list[Stream]) -> float:
    return sum(stream.mass for stream in streams)


def mixed_composition(streams: list[Stream]) -> dict[str, float]:
    total = total_mass(streams)
    if total <= 0:
        raise ValueError("Total stream mass must be positive")
    components = set().union(*(stream.composition for stream in streams))
    return {
        component: round(
            sum(component_mass(stream, component) for stream in streams)
            / total * 100.0,
            6,
        )
        for component in sorted(components)
    }


def closure(feed_mass: float, product_mass: float, tolerance: float = 1e-9) -> bool:
    if feed_mass < 0 or product_mass < 0:
        raise ValueError("Mass values cannot be negative")
    return abs(feed_mass - product_mass) <= tolerance
