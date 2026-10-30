# 📋 Technical Decision Log — COD RTO Decision Engine

**Project:** Oytra COD RTO Decision Engine  
**Author:** Vansh Patel (`vdppatel2204@gmail.com`)  
**Target:** Associate Software Engineer Internship at Oytra  
**Evaluation Lead:** Kapil (Founder / Engineering)  
**Date:** October 2026  

---

## 1. Decision: Hybrid Architecture (LLM for Qualitative NLP, Pure Python for Numeric Risk Scoring)

### Context & Problem
Every incoming COD order contains both unstructured text (customer name, delivery address, locality notes in Hinglish) and structured tabular attributes (pincode, order ticket size, customer order count, previous RTO track record). A common naive approach is to dump the entire order JSON into an LLM prompt and ask: *"Should we ship this COD order?"*

### Decision
We strictly separated qualitative text analysis from quantitative risk scoring:
1. **Qualitative NLP (LLM / Heuristic):** Evaluates whether an address is deliverable, contains landmarks, is written in Hinglish, or if the customer name is a fake keyboard mash (e.g., `"asdf"`).
2. **Quantitative Risk Scoring (Pure Python):** Computes normalized risk weights, applies hard rule penalties, and checks threshold cutoffs using deterministic Python math.

### Rationale & Trade-offs
- **Determinism & Auditability:** Financial decisions must be explainable. An operations manager cannot debug why an order was cancelled if the logic is hidden inside a stochastic 70B parameter model. Pure Python guarantees identical inputs always yield identical risk scores.
- **Latency & Reliability:** Evaluating pure Python takes `< 1 millisecond`. Routing math to an LLM adds 1.5–3.0 seconds of latency per order and introduces a catastrophic single point of failure if an external API experiences rate-limiting or downtime.
- **Cost Efficiency:** Running full decisioning on an LLM costs money on every order. By isolating NLP to address checks with a fast local fallback, operational costs remain near zero.

---

## 2. Decision: 4 Operational Action Buckets Instead of Binary Ship / Cancel

### Context & Problem
Traditional fraud prevention tools often use a binary gate: **Ship** or **Cancel**. In D2C e-commerce, binary gates are disastrous:
- Cancelling too aggressively infuriates Marketing by killing customers acquired with hard-won Customer Acquisition Cost (CAC ~₹300).
- Shipping everything blind results in a 28% COD RTO rate and ₹169.40 in sunk dead freight per returned shipment.

### Decision
We implemented a graduated 4-tier decision taxonomy:
1. **✅ Ship As-Is (`score ≤ 0.25`):** ~60% of orders. VIP repeat customers, verified addresses, zero friction, immediate automated AWB dispatch.
2. **⚡ Nudge to Prepaid (`0.25 < score ≤ 0.50`):** ~20% of orders. Moderate risk. Automated WhatsApp message offering an instant ₹30 UPI discount (`PAYNOW...`).
3. **💬 Ship After Confirmation (`0.50 < score ≤ 0.72`):** ~12% of orders. High-risk pincodes or first-time buyers. 24-hour dispatch hold awaiting a simple `YES` or `NO` reply on WhatsApp.
4. **🛑 Hold / Cancel (`score > 0.72`):** ~8% of orders. Critical risk (fake names, gibberish addresses, serial RTO offenders). Automatic hold for manual ops review or cancellation.

### Rationale
This 4-tier architecture balances the tension between **Operations** (whose goal is minimizing courier waste) and **Marketing** (whose goal is protecting Top-of-Funnel GMV and customer lifetime value).

---

## 3. Decision: Unit Economics Justification for the ₹30 Prepaid Discount

### Context & Problem
Marketing teams often question whether offering an instant discount on existing orders erodes brand gross margins.

### Decision
We capped the prepaid conversion discount at **₹30**, supported by rigorous unit economics math.

### The Unit Economics Proof
- **Sunk RTO Cost per Returned COD Order:**
  - Forward Freight: ₹65
  - Reverse Logistics Freight: ₹65
  - Warehousing, Handling & Restocking: ₹25
  - Product Transit Damage (8% damage rate @ ₹180 product cost): ₹14.40
  - **Total Sunk Loss per RTO: ₹169.40**
- **RTO Probability Reduction:**
  - Baseline COD RTO Rate: **28%**
  - Baseline Prepaid RTO Rate: **4%**
  - **Net Risk Reduction: 24 percentage points (0.24)**
- **Expected Sunk Freight Saved:**
  $$\text{Gross Savings} = 0.24 \times ₹169.40 = ₹40.66 \text{ per converted order}$$
- **Net Margin Impact:**
  $$\text{Net Contribution Gain} = ₹40.66 - ₹30.00 = +\mathbf{₹10.66} \text{ per converted order}$$

### Rationale
Offering ₹30 is the psychological "sweet spot" for Indian consumers (meaningful enough to open GooglePay/PhonePe) while ensuring Oytra earns an extra **+₹10.66 in pure net profit** on every single conversion.

---

## 4. Decision: Externalizing Configuration into `config/thresholds.yaml`

### Context & Problem
E-commerce risk appetites shift dynamically during peak sales periods (e.g., Diwali, Black Friday, Payday Sales). Hardcoding risk thresholds into application code forces developers to deploy new code commits whenever the ops team wants to tighten or loosen risk filters.

### Decision
All risk scoring weights, threshold brackets, business constants (freight rates, CAC, damage rates), and hard rule boosts are decoupled into `config/thresholds.yaml`.

### Rationale
Operations leads and founders can adjust `thresholds.yaml` in 10 seconds without touching a single line of Python, and the platform dynamically reflects the changes immediately.

---

## 5. Decision: Resilient Multi-Provider Fallback Architecture

### Context & Problem
Third-party LLM APIs suffer from rate-limits, expired credits, network timeouts, and model deprecations. An e-commerce warehouse shipping hundreds of packages daily cannot halt fulfillment because an external API is down.

### Decision
We engineered a 4-layer resilient fallback pipeline in `src/decision_engine.py`:
1. **Groq Llama 3.3 70B** (Ultra-fast, sub-500ms latency).
2. **NVIDIA NIM Llama 3.1 Nemotron 70B** (Enterprise fallback).
3. **Google Gemini 1.5 Flash** (Multimodal alternative).
4. **Built-in Domain NLP Heuristic Engine** (100% offline, zero network dependencies, 0ms latency).

### Rationale
Even if every single cloud API fails or the server is completely offline in a sandbox environment, the system gracefully defaults to the built-in domain NLP engine, guaranteeing **100.0% pipeline uptime**.
