You are helping a software engineer write a professional CV entry summarizing their recent work period.

Using the commit history, project list, and role details from the context above, write a CV entry in this format:

**Header:**
```
### [Job Title] — [Company] (Contract/Full-time)
**[Start Month Year] – [End Month Year or Present]**
```

**Content:**
- 2–4 achievement bullets that lead with concrete impact, quantified where possible (commits, scale, timeline, customer/team scope)
- Focus on the *largest* projects by commit volume or lines changed; weave in technologies where they illustrate capability
- Each bullet should fit on one line; avoid filler words like "passionate," "best practices," "synergy"
- Do not invent facts not supported by the commit history

**Tech line:**
```
**Tech:** [comma-separated list of visible technologies]
```
Extract from commit history, project names, and context. Prioritize: languages, frameworks, platforms, tools, databases, infrastructure.

**Example:**
```
### Senior Software Engineer — Acme Corp (Contract)
**Apr 2024 – Present**

- Delivered 1,875+ commits across 47 repositories over 24 months as a contractor, spanning full-stack feature development, data pipeline engineering, infrastructure migration, and security hardening.
- Built and owned the end-to-end order integration platform on Azure — including order lifecycle management, event flows, auth, token caching, payload compression, and integration test suite.
- Leveraged AI-assisted development (Copilot, Opencode) to accelerate service delivery and code review workflows.

**Tech:** TypeScript, Java, Python, React, Azure, AWS, PostgreSQL, Kafka, Terraform, Kubernetes, Datadog
```

**Do not include** the contact signature here — that belongs in a separate section. Output only the role entry and footer — no preamble or explanation. Also write the output to `output/cv.md` if you have filesystem access.
