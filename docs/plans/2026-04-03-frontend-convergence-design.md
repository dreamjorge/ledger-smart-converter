# Frontend Convergence Design

**Date**: 2026-04-03
**Status**: Accepted
**Scope**: Documentation-only architecture decision for the current coexistence of Streamlit and Flet.

## Decision Checklist

- **Is Streamlit temporary or permanent?** Streamlit is the current **primary UI** and the supported runtime baseline. It is **not treated as a temporary shim** during this remediation phase.
- **Is Flet primary or experimental?** Flet is **experimental**, useful for desktop validation and adapter learning, but it is **not the primary UI** yet.
- **What parity guarantee exists during coexistence?** The coexistence **parity guarantee** is limited to critical user workflows already encoded in shared services and smoke coverage: import entrypoints, analytics entrypoints, manual entry category loading, rule-hub category loading, and settings/profile switching.
- **What criteria allow removing one adapter?** We can remove one adapter only when the remaining adapter fully covers the guaranteed workflows, no unique production-only workflow depends on the removed adapter, launch/docs/scripts point to a single default UI, and verification/docs are updated in the same change.

## Why This Decision Exists

The repository currently ships two UI adapters:

- `src/web_app.py` and `src/ui/pages/` for Streamlit
- `src/flet_app.py` and `src/ui/flet_ui/` for Flet

That coexistence created ambiguity after the merge: some docs described an active migration to Flet, while the broader project guidance still treated Streamlit as the main supported interface and referred to Flet as a prototype. This document makes the current contract explicit so runtime behavior stays unchanged but architecture expectations stop drifting.

## Frontend Convergence Decision

### 1. Supported runtime today

Streamlit remains the **primary UI** for the current project baseline.

- It is the default web runtime documented in the project overview.
- It remains the reference adapter for feature availability and support expectations.
- It should not be described as legacy-only or assumed removable without a separate follow-up decision.

### 2. Role of the Flet adapter

Flet remains **experimental** during the remediation window.

- It is valuable for desktop UX exploration and for proving shared service boundaries.
- It is not yet the authoritative source of UI behavior.
- Work on Flet should preserve coexistence with Streamlit instead of forcing a silent migration narrative.

### 3. Coexistence parity guarantee

During coexistence, parity means **critical workflow parity**, not pixel or interaction parity.

The guaranteed shared workflows are:

1. import entrypoints exist in both adapters
2. analytics entrypoints exist in both adapters
3. manual entry loads canonical categories through shared config/service contracts
4. rule hub loads canonical categories through shared config/service contracts
5. settings/profile switching exists in both adapters through shared user-service helpers

Anything beyond those flows is best-effort until a later graduation decision promotes one adapter to sole ownership.

### 4. Criteria to remove one adapter

Removing Flet is allowed if:

- desktop experimentation is no longer an active project priority
- Streamlit still covers all guaranteed workflows
- no release, support, or operator workflow depends exclusively on Flet
- the removal updates docs, scripts, and verification references together

Removing Streamlit is allowed if:

- Flet graduates from experimental to **primary UI** through an explicit follow-up decision
- Flet covers every guaranteed coexistence workflow without Streamlit fallbacks
- launch scripts, onboarding docs, and verification commands all point to Flet as the single supported adapter
- the parity smoke assumptions and UI context docs are rewritten in the same change to reflect single-adapter ownership

## Consequences

- Documentation should stop implying an automatic or already-approved migration away from Streamlit.
- Flet work can continue, but as experimental hardening rather than as an assumed replacement.
- Shared services and smoke coverage remain the enforcement layer for the coexistence parity guarantee.
- Any future move to make Flet the primary UI requires a new explicit decision doc rather than inference from roadmap wording.

## Non-Goals

- This decision does not remove either adapter.
- This decision does not change runtime startup scripts or default commands.
- This decision does not require visual parity between Streamlit and Flet.
