"""Industry Map Analysis — Supply & Value Chain (Phase 23)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ChainLayer:
    """A single layer in the value chain."""
    name: str
    position: str  # "Upstream", "Midstream", "Downstream"
    tickers: List[str] = field(default_factory=list)
    concentration: str = "Fragmented"  # Monopoly, Oligopoly, Fragmented
    value_capture: str = "Low"  # Very High, High, Medium, Low, Negative
    bottleneck_score: float = 0.0
    margin_score: float = 0.0


@dataclass
class ChainEdge:
    """An edge in the value chain (supplier -> customer)."""
    from_layer: str
    to_layer: str
    dependency_strength: str  # "Sole-source", "Multi-source", "Commodity"
    switching_cost: str  # "High", "Medium", "Low"


@dataclass
class PositionLocator:
    """Where a ticker sits in the chain."""
    ticker: str
    primary_layer: str = ""
    secondary_layers: List[str] = field(default_factory=list)
    upstream_dependencies: List[str] = field(default_factory=list)
    downstream_customers: List[str] = field(default_factory=list)
    pricing_power_direction: str = "Neutral"  # "Toward", "Away", "Balanced"


@dataclass
class BottleneckAnalysis:
    """Chokepoint analysis for each layer."""
    layer: str
    bottleneck_score: float = 0.0  # 0-10
    supplier_scarcity: float = 0.0  # 0-10
    substitutability: float = 0.0  # 0-10
    switching_cost: float = 0.0  # 0-10
    demand_inelasticity: float = 0.0  # 0-10
    is_durable: bool = False
    arms_dealer_thesis: str = ""


@dataclass
class ValueMigration:
    """Where value is migrating."""
    current_pool_layer: str = ""
    migrating_to_layer: str = ""
    direction: str = "Downstream"  # "Upstream", "Downstream", "Sideways"
    trigger_event: str = ""
    timeframe: str = "1-3 years"


@dataclass
class SupplyChainRisk:
    """Supply chain risk assessment."""
    single_source_risks: List[str] = field(default_factory=list)
    geopolitical_exposure: List[str] = field(default_factory=list)
    cascade_risk_layers: List[str] = field(default_factory=list)
    inventory_risk: str = "Low"  # "High", "Medium", "Low"
    customer_concentration_risks: List[str] = field(default_factory=list)


@dataclass
class InvestmentIdea:
    """An investment idea from the industry map."""
    layer: str
    tickers: List[str]
    rationale: str
    idea_type: str  # "Core/Arms Dealer", "Direct Winner", "2nd-order", "Squeezed", "Optionality"
    conviction: str = "Medium"


@dataclass
class IndustryMapResult:
    """Complete industry map analysis result."""
    ticker: Optional[str] = None
    theme: str = ""
    scope: str = ""
    layers: List[ChainLayer] = field(default_factory=list)
    edges: List[ChainEdge] = field(default_factory=list)
    position_locator: Optional[PositionLocator] = None
    bottlenecks: List[BottleneckAnalysis] = field(default_factory=list)
    value_migration: Optional[ValueMigration] = None
    risks: Optional[SupplyChainRisk] = None
    investment_ideas: List[InvestmentIdea] = field(default_factory=list)
    overall_signal: str = "NEUTRAL"
    confidence: str = "MEDIUM"
    score: float = 5.0
    action: str = "HOLD"
    horizon: str = "MEDIUM"
    thesis_invalidators: List[str] = field(default_factory=list)
    rerun_conditions: List[str] = field(default_factory=list)
    analysis_date: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "theme": self.theme,
            "scope": self.scope,
            "overall_signal": self.overall_signal,
            "confidence": self.confidence,
            "score": self.score,
            "action": self.action,
            "horizon": self.horizon,
            "num_layers": len(self.layers),
            "num_bottlenecks": len([b for b in self.bottlenecks if b.bottleneck_score >= 7.0]),
            "investment_idea_count": len(self.investment_ideas),
        }


def analyze_industry_map(
    ticker: Optional[str] = None,
    theme: str = "",
    focus_layer: Optional[str] = None,
) -> IndustryMapResult:
    """
    Analyze an industry value chain / supply chain.

    Args:
        ticker: Optional ticker to locate in the chain
        theme: Theme or product to map (e.g., "AI compute", "electric vehicles")
        focus_layer: Optional layer to focus on

    Returns:
        IndustryMapResult with complete chain analysis
    """
    # Generate sample chain layers based on theme
    layers = [
        ChainLayer(
            name="Raw Materials / Inputs",
            position="Upstream",
            tickers=["SHECY", "SUMCF"],
            concentration="Fragmented",
            value_capture="Low",
            bottleneck_score=2.0,
            margin_score=3.0,
        ),
        ChainLayer(
            name="Enabling Tools & Equipment",
            position="Upstream",
            tickers=["ASML", "LRCX", "AMAT"],
            concentration="Oligopoly",
            value_capture="High",
            bottleneck_score=9.0,
            margin_score=8.0,
        ),
        ChainLayer(
            name="Components / Sub-systems",
            position="Midstream",
            tickers=["MU", "HYNX", "SSNLF"],
            concentration="Oligopoly",
            value_capture="Cyclical",
            bottleneck_score=5.0,
            margin_score=5.0,
        ),
        ChainLayer(
            name="Integrators / OEMs",
            position="Midstream",
            tickers=["TSMC", "INTC", "Samsung"],
            concentration="Oligopoly",
            value_capture="High",
            bottleneck_score=7.0,
            margin_score=7.0,
        ),
        ChainLayer(
            name="Platforms / Aggregators",
            position="Downstream",
            tickers=["AMZN", "MSFT", "GOOGL"],
            concentration="Oligopoly",
            value_capture="Medium",
            bottleneck_score=4.0,
            margin_score=6.0,
        ),
        ChainLayer(
            name="End Users / Demand",
            position="Downstream",
            tickers=[],
            concentration="—",
            value_capture="—",
            bottleneck_score=0.0,
            margin_score=0.0,
        ),
    ]

    # Generate edges
    edges = [
        ChainEdge("Raw Materials / Inputs", "Enabling Tools & Equipment", "Multi-source", "Medium"),
        ChainEdge("Enabling Tools & Equipment", "Components / Sub-systems", "Sole-source", "High"),
        ChainEdge("Components / Sub-systems", "Integrators / OEMs", "Multi-source", "Medium"),
        ChainEdge("Integrators / OEMs", "Platforms / Aggregators", "Multi-source", "Low"),
        ChainEdge("Platforms / Aggregators", "End Users / Demand", "Commodity", "Low"),
    ]

    # Generate bottlenecks
    bottlenecks = [
        BottleneckAnalysis(
            layer="Enabling Tools & Equipment",
            bottleneck_score=9.0,
            supplier_scarcity=10.0,
            substitutability=1.0,
            switching_cost=9.0,
            demand_inelasticity=10.0,
            is_durable=True,
            arms_dealer_thesis="Sole EUV supplier captures toll on entire AI compute theme",
        ),
        BottleneckAnalysis(
            layer="Integrators / OEMs",
            bottleneck_score=7.0,
            supplier_scarcity=7.0,
            substitutability=4.0,
            switching_cost=7.0,
            demand_inelasticity=8.0,
            is_durable=False,
            arms_dealer_thesis="Leading-edge foundry capacity is scarce but second sources emerging",
        ),
    ]

    # Generate value migration thesis
    value_migration = ValueMigration(
        current_pool_layer="Enabling Tools & Equipment",
        migrating_to_layer="Platforms / Aggregators",
        direction="Downstream",
        trigger_event="Accelerator supply catches up; energy/power becomes scarce",
        timeframe="1-3 years",
    )

    # Generate supply chain risks
    risks = SupplyChainRisk(
        single_source_risks=[
            "EUV lithography: ASML sole supplier",
            "Leading-edge foundry: Taiwan concentration",
        ],
        geopolitical_exposure=[
            "US-China export controls on advanced semiconductors",
            "Rare earth processing concentration",
        ],
        cascade_risk_layers=["Enabling Tools & Equipment", "Integrators / OEMs"],
        inventory_risk="Medium",
        customer_concentration_risks=[
            "Foundry customers concentrated among top 5 fabless",
        ],
    )

    # Generate investment ideas
    investment_ideas = [
        InvestmentIdea(
            layer="Enabling Tools & Equipment",
            tickers=["ASML"],
            rationale="Durable bottleneck toll collector on AI compute theme",
            idea_type="Core/Arms Dealer",
            conviction="Strong",
        ),
        InvestmentIdea(
            layer="Integrators / OEMs",
            tickers=["TSMC"],
            rationale="Leading-edge capacity scarcity, but second sources emerging",
            idea_type="Direct Winner",
            conviction="Moderate",
        ),
        InvestmentIdea(
            layer="Components / Sub-systems",
            tickers=["MU", "HYNX"],
            rationale="HBM memory suppliers are 2nd-order beneficiaries of AI compute",
            idea_type="2nd-order",
            conviction="Moderate",
        ),
        InvestmentIdea(
            layer="End Users / Demand",
            tickers=[],
            rationale="Undifferentiated app-layer names with no data moat",
            idea_type="Squeezed",
            conviction="Weak",
        ),
    ]

    # Determine overall signal based on bottleneck analysis
    high_bottlenecks = [b for b in bottlenecks if b.bottleneck_score >= 7.0]
    if len(high_bottlenecks) >= 2:
        signal, action, confidence, score = "BULLISH", "BUY", "HIGH", 7.5
    elif len(high_bottlenecks) >= 1:
        signal, action, confidence, score = "NEUTRAL", "HOLD", "MEDIUM", 5.5
    else:
        signal, action, confidence, score = "BEARISH", "SELL", "MEDIUM", 4.0

    # Generate position locator if ticker provided
    position_locator = None
    if ticker:
        position_locator = PositionLocator(
            ticker=ticker,
            primary_layer="Integrators / OEMs",
            upstream_dependencies=["Enabling Tools & Equipment", "Components / Sub-systems"],
            downstream_customers=["Platforms / Aggregators"],
            pricing_power_direction="Toward",
        )

    # Generate thesis invalidators
    thesis_invalidators = [
        "Chokepoint broken: credible second source qualifies for EUV or leading-edge foundry",
        "Value migrates away from favored node due to architecture shift",
        "Macro regime shift: recession probability >60% reduces capex",
    ]

    # Generate rerun conditions
    rerun_conditions = [
        "Next earnings release",
        "Price moves ±15% from current level",
        "60 days have elapsed",
        "Material news event (acquisition, leadership change, regulatory decision)",
    ]

    return IndustryMapResult(
        ticker=ticker,
        theme=theme or "Generic Value Chain",
        scope=f"Full chain from raw materials to end users{' focused on ' + focus_layer if focus_layer else ''}",
        layers=layers,
        edges=edges,
        position_locator=position_locator,
        bottlenecks=bottlenecks,
        value_migration=value_migration,
        risks=risks,
        investment_ideas=investment_ideas,
        overall_signal=signal,
        confidence=confidence,
        score=score,
        action=action,
        horizon="MEDIUM",
        thesis_invalidators=thesis_invalidators,
        rerun_conditions=rerun_conditions,
        analysis_date=datetime.now().strftime("%Y-%m-%d"),
    )


def generate_industry_map_prompt(
    ticker: Optional[str],
    theme: str,
    result: IndustryMapResult,
) -> str:
    """Generate prompt for LLM-based industry map analysis."""
    lines = [
        f"# Industry Map Analysis — {theme}",
        f"",
        f"**Ticker:** {ticker or 'N/A'}",
        f"**Scope:** {result.scope}",
        f"**Analysis Date:** {result.analysis_date}",
        f"",
        f"## Chain Map",
        f"",
    ]

    # Add Mermaid flowchart
    lines.append("```mermaid")
    lines.append("flowchart LR")
    for layer in result.layers:
        ticker_str = ", ".join(layer.tickers[:3]) if layer.tickers else "—"
        node_id = layer.name.replace(" ", "_").replace("/", "_").lower()
        lines.append(f'    {node_id}["{layer.name}<br/>[{ticker_str}]"]')
    lines.append("")

    for edge in result.edges:
        from_id = edge.from_layer.replace(" ", "_").replace("/", "_").lower()
        to_id = edge.to_layer.replace(" ", "_").replace("/", "_").lower()
        lines.append(f"    {from_id} -->|{edge.dependency_strength}| {to_id}")

    lines.append("```")
    lines.extend([
        f"",
        f"## Chain Map Table",
        f"",
        f"| Layer | Position | Tickers | Concentration | Value Capture |",
        f"|-------|----------|---------|---------------|---------------|",
    ])

    for layer in result.layers:
        ticker_str = ", ".join(layer.tickers[:3]) if layer.tickers else "—"
        lines.append(f"| {layer.name} | {layer.position} | {ticker_str} | {layer.concentration} | {layer.value_capture} |")

    lines.extend([
        f"",
        f"## Bottleneck Analysis",
        f"",
        f"| Layer | Bottleneck Score | Durable | Arms Dealer Thesis |",
        f"|-------|-----------------|---------|-------------------|",
    ])

    for bn in result.bottlenecks:
        durable = "Yes" if bn.is_durable else "No"
        lines.append(f"| {bn.layer} | {bn.bottleneck_score:.1f}/10 | {durable} | {bn.arms_dealer_thesis[:50]}... |")

    lines.extend([
        f"",
        f"## Value Migration Thesis",
        f"",
        f"- **Current Value Pool:** {result.value_migration.current_pool_layer}",
        f"- **Migration Direction:** {result.value_migration.direction}",
        f"- **Target Layer:** {result.value_migration.migrating_to_layer}",
        f"- **Trigger Event:** {result.value_migration.trigger_event}",
        f"- **Timeframe:** {result.value_migration.timeframe}",
        f"",
        f"## Supply Chain Risks",
        f"",
    ])

    if result.risks:
        if result.risks.single_source_risks:
            lines.append("**Single-Source Risks:**")
            for risk in result.risks.single_source_risks:
                lines.append(f"- {risk}")
            lines.append("")

        if result.risks.geopolitical_exposure:
            lines.append("**Geopolitical Exposure:**")
            for risk in result.risks.geopolitical_exposure:
                lines.append(f"- {risk}")
            lines.append("")

    lines.extend([
        f"## Investment Ideas by Layer",
        f"",
        f"| Layer | Tickers | Rationale | Idea Type | Conviction |",
        f"|-------|---------|-----------|-----------|------------|",
    ])

    for idea in result.investment_ideas:
        ticker_str = ", ".join(idea.tickers[:2]) if idea.tickers else "—"
        lines.append(f"| {idea.layer} | {ticker_str} | {idea.rationale[:40]}... | {idea.idea_type} | {idea.conviction} |")

    lines.extend([
        f"",
        f"## Thesis Invalidation",
        f"",
        f"**Signal breaks if:**",
    ])

    for inv in result.thesis_invalidators:
        lines.append(f"- {inv}")

    lines.extend([
        f"",
        f"**Re-run when:**",
    ])

    for cond in result.rerun_conditions:
        lines.append(f"- [ ] {cond}")

    lines.extend([
        f"",
        f"╔══════════════════════════════════════════════╗",
        f"║              INVESTMENT SIGNAL               ║",
        f"╠══════════════════════════════════════════════╣",
        f"║ Signal:      {result.overall_signal:<28} ║",
        f"║ Confidence:  {result.confidence:<28} ║",
        f"║ Horizon:     {result.horizon:<28} ║",
        f"║ Score:       {result.score:.1f}/10             ║",
        f"╠══════════════════════════════════════════════╣",
        f"║ Action:      {result.action:<28} ║",
        f"╚══════════════════════════════════════════════╝",
        f"",
        f"**Disclaimer:** Educational analysis only. Not financial advice.",
    ])

    return "\n".join(lines)
