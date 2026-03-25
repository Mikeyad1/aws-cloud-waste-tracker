# Product Positioning Notes

This document captures the product framing that guides UX and engineering decisions in Cloud Waste Tracker.

## Core framing

- **One question:** "How much are we wasting—and what do we do about it?"
- **One number:** a monthly waste estimate derived from scan results.
- **One list:** a prioritized set of recommendations with estimated impact and actionable steps.

## UX principles that influence the implementation

- The waste number is presented first; deeper breakdowns are available via drill-down.
- Each recommendation includes explanation content (for example, the inputs/calculation notes behind the estimate).
- The app supports a synthetic mode so the end-to-end experience (UI -> parsing -> recommendation rendering) can be tested without live AWS access.

## Where this shows up in the code

- Waste page UI: `src/cwt_ui/pages/1_Waste.py`
- Recommendation normalization and list building: `src/cwt_ui/utils/unified_recommendations.py` and related services

