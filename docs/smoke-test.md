# Smoke Tests

This document is a product-level smoke map: each item is a user goal Refine
should continue to support. When the application changes significantly, ask a
coding agent to regenerate this document from the current codebase instead of
editing the list by memory. The agent should inspect the Guide, routes, command
registry, API surface, CLI, and existing tests, then rewrite the list around the
current user journeys and product lifecycle. Keep the result concise,
outcome-oriented, and organized by framing rather than by implementation module.

## Core Product Loop

1. Start a clean Refine instance on port 8080.
2. Open the Refine browser UI.
3. Attach an existing application.
4. Configure how Refine starts, stops, rebuilds, and checks the application.
5. Start the application from Refine.
6. Create a Gap describing a desired behavior change.
7. Move the Gap into agent work.
8. Inspect the agent's progress and logs.
9. Review the completed Gap.
10. Verify the Gap.
11. Confirm the merged work appears in Changes.

## Application Lifecycle

12. Create a new application.
13. Clone and attach an application from a Git URL.
14. Swap to another known application.
15. Remove the current application from the local checkout.
16. Recover from no-app mode by attaching an application.
17. Generate target-application commands with AI.
18. Confirm the target application reports healthy.
19. Rebuild the target application after merged work.

## Guided Setup

20. Complete the Get Started checklist for a newly attached app.
21. Find field-level setup help in the Guide reference.
22. Use the Guide to navigate directly to the relevant setup control.

## Work Intake

23. Select the reporter for new work.
24. Manage reporters without losing historical Gap attribution.
25. Import multiple Gaps from pasted feedback or CSV.
26. Find relevant Gaps by status, reporter, node, text, or activity metadata.
27. Bulk-edit selected Gaps from the Gaps list.
28. Retry failed Gaps from their last safe workflow state.

## Gap Management

29. Open a Gap without losing the current screen context.
30. Add a new round of feedback to a Gap.
31. Change a Gap's name, priority, or reporter.
32. Move a Gap between backlog, todo, review, done, failed, and cancelled states where user action is allowed.
33. Cancel or delete a Gap.
34. Open chat with the agent using Gap context.
35. Draft Gaps from a planning chat.

## Review And Quality

36. See all review work assigned to the active reporter.
37. Verify multiple review Gaps from the dashboard.
38. Send reviewed work back to todo when it needs another pass.
39. Review Governance output for a Gap.
40. Review Quality output for a Gap.
41. Configure project Governance context, constitution, and rules.
42. Configure project Guidance that applies only to matching Gaps.
43. Configure Quality requirements, instructions, gates, and managed regressions.

## Navigation And Evidence

44. Understand current work status from the dashboard.
45. Compare current-node work with all-node work.
46. Browse and search target-application files.
47. Read a large target-application file.
48. View activity logs for the project.
49. Open logs for a specific Gap.
50. Filter logs to find relevant activity.
51. Search merged Changes.

## Local Operation

52. Check Refine status from the CLI.
53. Restart Refine from the CLI.
54. Stop Refine from the CLI.
55. Install Refine as a persistent service.
56. Uninstall the persistent service.
57. Reset the local Refine binding.
58. Run Refine diagnostics.
59. Run the repository test suite.
60. Update Refine to the latest release.

## Runtime Control

61. Configure the AI provider and re-check authentication.
62. Configure runtime limits for agents.
63. Pause and unpause agent scheduling.
64. Stop a stale agent or chat process.
65. Inspect runner processes and background jobs.
66. View and filter runtime performance metrics.

## Multi-Node And Cluster

67. Create and activate a node for the current machine.
68. Copy node settings from another node.
69. Transfer work between nodes.
70. Register and list cluster nodes.
71. Bootstrap a cluster node over SSH.
72. Run a Refine command on a remote cluster node.
73. Sync project state through Git.
74. Run project-state migration status.
75. Run a required project-state migration.

## Support

76. Report a Refine bug or feature request.

## Distributed Team Workflow

Refine's headline use case is running it across a team: each teammate runs their
own Refine instance (a separate port, or a separate machine) attached to a clone
of one shared repo, and the instances coordinate by pushing and pulling
`.refine/` state through a shared Git remote. This is the end-to-end journey a
team actually exercises, building on the atomic node, reporter, and Git-sync
capabilities above (24, 45, 67-69, 73).

77. Run a separate Refine instance per teammate, each on its own port or machine, against the same project.
78. Join an existing team project by cloning its Git remote and adopting the shared Refine state.
79. Give each instance its own work-owning node and its own reporters.
80. Raise work on one node and publish it to the team through the shared Git remote.
81. Pull teammates' work from the remote so every node converges on the same backlog.
82. Keep node ownership and reporter attribution intact as work propagates between nodes.
83. Read both a single node's queue and the cluster's aggregate backlog.

## Feature Organization

A Feature is an ordered collection of Gaps for planning and executing larger
work, without replacing the standalone Gap workflow. Features are node-bound like
Gaps, derive their status and progress from their Gaps rather than carrying their
own mutable workflow state, and serialize execution within a Feature while letting
different Features run in parallel. Features do not appear on the Dashboard.

84. Create a Feature to plan larger work as an ordered set of Gaps.
85. Add new or existing Gaps to a Feature and order them for execution.
86. Reorder Gaps within a Feature to change the execution sequence.
87. Remove a Gap from a Feature without deleting the Gap.
88. Track a Feature's derived status and progress as its Gaps advance.
89. Browse, search, and filter Features by derived status.
90. Update a Feature's name and description.
91. Import a batch of Gaps as a new Feature, or append them to an existing one.
92. Plan a Feature with ordered Gaps by default from a planning chat.
93. Cancel a Feature, cascading to its non-terminal Gaps.
94. Delete a Feature, cascading to its Gaps.
95. Serialize agent work within a Feature while running different Features in parallel.
