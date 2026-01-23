How to Enforce Code Scalpel in Your RepoTo prevent "Vibe Coding" and ensure all AI-generated code is verified, add this workflow to your repository.1. Create the Workflow FileCreate .github/workflows/enforce-scalpel.yml:name: Enforce AI Safety
on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  verify-agent-integrity:
    runs-on: ubuntu-latest
    # Only run this check if the PR author is a known bot/agent
    if: |
      contains(github.actor, '[bot]') || 
      github.actor == 'renovate' || 
      github.actor == 'dependabot'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Verify Code Scalpel Proof
        uses: tescolopio/verify-scalpel-proof-action@v1
        with:
          proof-path: ".scalpel/verification.json"
          strict-mode: "true"
2. What Happens Next?The Agent Opens a PR: If an unconfigured agent (like standard Copilot or a custom script) opens a PR without using Code Scalpel tools, this workflow will fail.The Block: The PR cannot be merged (if you have "Require status checks to pass" enabled).The Fix: The developer must configure their agent to use the code-scalpel MCP server. Once the agent uses Scalpel to make the edits, Scalpel automatically generates the .scalpel/verification.json proof file.The Pass: The workflow sees the valid proof and passes.3. Why This WorksZero-Trust: We don't trust the agent's intent; we verify its artifact.Vendor Agnostic: It doesn't matter if you use Claude, OpenAI, or Llama. If they don't produce the proof, they don't get merged.