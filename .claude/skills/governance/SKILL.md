---
name: governance
description: Run EditHealth governance. "/governance audit <base label | Box folder | file>" checks indexing, filing, vocabularies, names, repositories, tags and events. "/governance workflow" shows the template creation workflow. "/governance change <what changed>" records a workflow change. "/governance ruling <ruling>" logs a ruling. Use whenever template work is filed, a workflow step is run or changed, or Ingrid gives a ruling.
---

# /governance

Hand the request to the `governance` agent (Agent tool, `subagent_type: governance`). Pass along Ingrid's words exactly, plus anything from this conversation that the agent needs: the base label, Box file or folder ids, and the step just run.

| Request | Agent task |
|---|---|
| `audit <target>` or no argument | Audit the target. With no target, audit the most recent step run in this conversation |
| `workflow` | Recall the workflow and, if a base is named, its next step |
| `change <what changed>` | Record a workflow change. Ask Ingrid who ruled it and when, if she hasn't said |
| `ruling <ruling>` | Log a ruling with Ingrid's name and today's date |

Give Ingrid the agent's verdict line and findings table as written. If the agent proposes a write to Box, Notion, Lucidchart or GitHub, ask Ingrid before making it.

When Ingrid gives a ruling or changes a step during other work, offer `/governance change` or `/governance ruling` in one line, so that the change gets recorded.
