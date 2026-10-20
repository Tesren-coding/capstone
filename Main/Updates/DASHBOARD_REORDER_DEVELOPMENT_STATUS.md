# Dashboard: module order and development status

The home dashboard and shared navigation now list **PQPR → Line Balancing → Line Builder** from left to right.

- PQPR: **In Development**, editor remains accessible to continue refinement.
- Line Balancing: **In Development**, editor remains accessible to continue refinement.
- Line Builder: **Available**, with all existing capabilities retained.
- The public module name is **Line Balancing** (without “& Yamazumi”). Its underlying chart functionality and internal file/module names are unchanged for compatibility.
- This is a UI/status change only: no route, storage, scenario, SQL or API schema changes.

**Deployment note:** “In Development” labels communicate project status; they do not restrict access to those URLs. Authentication/authorization and production hosting are separate deployment steps.
