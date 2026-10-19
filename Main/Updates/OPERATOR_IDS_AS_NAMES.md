# Operator IDs are now their only names

- The Line Builder does not offer a separate operator name input. Operators are displayed as `Op1`, `Op2`, etc. in the editor, on the canvas, and in the simulation hover legend.
- The `name` field is retained in saved scenario JSON for backwards compatibility, but is derived from the operator ID. Older custom names are replaced **in memory** on load/validation and reflected on the next save; stored originals are not overwritten until explicitly saved.
- New operators and operators pasted using Ctrl+V receive the lowest available positive `Op` number. Deleting `Op2` does not rename the other operators; the next new/pasted operator uses `Op2`.
- Use **Renumber Operators** on the Line Builder toolbar to close gaps in existing saved lines (`Op1`, `Op3`, `Op5` -> `Op1`, `Op2`, `Op3`). Confirm before renumbering. The operator properties, process sequences, home attachments, and colors follow each operator. Source balancing IDs stay in `source_operator_id`.
- If the line was generated from balancing, its original operator names are still retained in the balancing plan/provenance, but the generated Line Builder operators are always `OpN`.
- No SQL schema migration or storage table changes are needed. The normalized scenario still has the `name` field for compatibility.
