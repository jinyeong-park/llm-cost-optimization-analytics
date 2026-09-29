"""
theme.py — Centralized design tokens for LLM Routing Analytics dashboard.

Color allocation rule:
  - Neutrals:  80–90% of the interface
  - Accent:     5–15% (focal series, hero numbers)
  - Semantic:   remainder (only for action-worthy status)

Model palette convention:
  - Haiku  → C_NAVY   (focal / winner / lower-cost efficient choice)
  - Sonnet → C_MUTED  (comparison / baseline / non-focal)
  - Routed → C_BLUE   (outcome / solution)
"""

# ── Canvas & surface ──────────────────────────────────────────────────────────
C_CANVAS  = "#F7F8FA"
C_SURFACE = "#FFFFFF"
C_BORDER  = "#D9DEE7"

# ── Text ──────────────────────────────────────────────────────────────────────
C_TEXT_PRIMARY   = "#18202B"
C_TEXT_SECONDARY = "#4E5B6B"
C_TEXT_MUTED     = "#6B7788"

# ── Accent ────────────────────────────────────────────────────────────────────
C_NAVY  = "#1F3864"   # primary accent — focal / positive / hero
C_BLUE  = "#2E75B6"   # secondary accent — outcome / solution

# ── Semantic ──────────────────────────────────────────────────────────────────
C_GREEN = "#087F5B"   # positive savings  (use sparingly — small markers only)
C_RED   = "#C53A4A"   # action-worthy risk only
C_AMBER = "#A15C00"   # watchlist / near-threshold

# ── Data series ───────────────────────────────────────────────────────────────
C_MUTED = "#B8C4D0"   # comparison / background / non-focal series

# ── Model palette ─────────────────────────────────────────────────────────────
MODEL_COLORS = {
    "haiku":  C_NAVY,   # focal: cheaper & often better
    "sonnet": C_MUTED,  # comparison baseline
    "routed": C_BLUE,   # the recommended outcome
}

# ── Shared Plotly layout defaults ─────────────────────────────────────────────
LAYOUT_DEFAULTS = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, system-ui, sans-serif", color=C_TEXT_SECONDARY, size=12),
    legend=dict(orientation="h", y=1.12, font=dict(size=11)),
    margin=dict(l=0, r=0, t=28, b=0),
    xaxis=dict(
        showgrid=False,
        linecolor=C_BORDER,
        tickfont=dict(size=11, color=C_TEXT_SECONDARY),
    ),
    yaxis=dict(
        gridcolor=C_BORDER,
        gridwidth=1,
        linecolor="rgba(0,0,0,0)",
        tickfont=dict(size=11, color=C_TEXT_SECONDARY),
        zeroline=False,
    ),
)


def apply_layout(fig, height=380, **overrides):
    """Apply shared layout defaults to a Plotly figure, then apply overrides."""
    cfg = dict(LAYOUT_DEFAULTS)
    cfg["height"] = height
    cfg.update(overrides)

    # Deep-merge xaxis/yaxis overrides
    for axis in ("xaxis", "yaxis"):
        if axis in overrides:
            merged = dict(LAYOUT_DEFAULTS.get(axis, {}))
            merged.update(overrides[axis])
            cfg[axis] = merged

    fig.update_layout(**cfg)
    return fig
