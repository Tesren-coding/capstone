# Operator-wide standing point selection

## Overview

Selecting a single operator in Line Builder now displays four dotted standing-point rings at **every station referenced by that operator’s action sequence**. This works for task-based Transfer, Process and Full Cycle assignments as well as legacy Pick, Work, Drop actions.

## How to use

1. Select an operator on the canvas. Dotted rings appear at all of its assigned stations.
2. Click **Top**, **Right**, **Bottom** or **Left** at any one station. The choice applies to all of this operator's actions at that station.
3. The new **Standing locations** section in the operator panel lists the settings by station. Choose **Auto** on a station's row to remove explicit sides for *all visits to that station*.
4. Selecting another operator shows that operator's own stations and settings, without affecting the first operator.

IN, OUT and SWIP boxes do not display standing-side rings: their movement destinations remain at their centers. Existing operator home attachment points stay independent of assignment standing sides.

## Data compatibility

This is an editor-only interaction change. The existing `operator.sequence[].standing_side` field is still used, so saved scenarios, walking geometry, playback and SWS/SWCS exports require no migration. Existing saves with differing sides among multiple actions at the same station display **Mixed** until the user chooses a unified side; they are **not automatically changed**.

## Tests

- Updated `tests/browser_walking_points.py` with multiple stations, repeated actions at the same station, multi-operator independence, zoom, dragging, Auto, serialization and New Line checks.
- Updated `tests/browser_operator_tasks.py` to exercise the simplified task panel.
