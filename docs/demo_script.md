# Demo Script
**OpenClaw2026_[TEAM_NAME]_WarungFlow**
*(Max 2 minutes)*

## 0:00–0:15 Problem
*Show the Streamlit UI homepage.*
"Many Indonesian UMKM sellers take orders via WhatsApp and accept payments via QRIS, but reconciling them at the end of the day is a manual nightmare. Unpaid orders slip through the cracks."

## 0:15–0:30 Solution
"Meet WarungFlow. Not a chatbot, but an autonomous finance operations agent. It acts as a back-office worker, reconciling orders and payments automatically."

## 0:30–1:20 Live demo
*Select Mock Mode (or DOKU mode).*
"Let's load sample data for Warung Bu Sari."
*Click 'Run WarungFlow Agent'.*
"I click one button. The agent takes over. It parses messy WhatsApp messages, loads QRIS transactions, and reconciles them."
*Scroll through the execution trace and reconciliation table.*
"Notice it flags an unpaid order. It then calculates cashflow health and generates a collection reminder."

## 1:20–1:45 Agent autonomy and technical architecture
*Show the Agent Execution Trace table.*
"This is the heart of the agent. The orchestrator loop continuously observes the state, decides the next action, calls the exact right tool, and updates memory. It creates DOKU payment requests for unpaid orders when configured, proving true tool-calling capability."

## 1:45–2:00 Impact and closing
*Show Export Reports panel.*
"Finally, it validates its work and exports a daily markdown report. WarungFlow transforms messy digital commerce into formal financial readiness. Thank you."
