"""
COD RTO Decision Engine
Classifies each COD order into one of 4 actions based on risk score.
LLM is used ONLY for qualitative judgments (address quality, name quality).
All math and threshold comparisons are done in pure Python.
"""

import yaml
import json
import os
from dataclasses import dataclass
from typing import Optional
from enum import Enum


# -----------------------------------------------------------------------------
# Action Enum
# -----------------------------------------------------------------------------

class Action(str, Enum):
    SHIP_AS_IS = "ship_as_is"
    NUDGE_TO_PREPAID = "nudge_to_prepaid"
    SHIP_AFTER_CONFIRMATION = "ship_after_confirmation"
    HOLD_CANCEL = "hold_cancel"

    def label(self):
        return {
            "ship_as_is": "✅ Ship as-is",
            "nudge_to_prepaid": "⚡ Nudge to prepaid",
            "ship_after_confirmation": "💬 Ship after confirmation",
            "hold_cancel": "🛑 Hold / Cancel",
        }[self.value]


# -----------------------------------------------------------------------------
# Input / Output Dataclasses
# -----------------------------------------------------------------------------

@dataclass
class OrderInput:
    order_id: str
    customer_name: str
    address: str
    pincode: str
    city: str
    state: str
    order_value: float
    is_first_order: bool = True
    customer_total_orders: int = 1
    customer_previous_rto_count: int = 0
    pincode_historical_rto_rate: float = 0.20   # 0.0 — 1.0
    num_items: int = 1
    product_category: str = ""


@dataclass
class DecisionOutput:
    order_id: str
    action: Action
    risk_score: float
    reason: str                  # plain-English, ops-friendly
    score_breakdown: dict
    llm_used: bool
    llm_flags: dict              # what LLM flagged


# -----------------------------------------------------------------------------
# Config Loader
# -----------------------------------------------------------------------------

def load_config(path: str = None) -> dict:
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "..", "config", "thresholds.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# -----------------------------------------------------------------------------
# LLM Providers (Multi-Provider Support: Groq, NVIDIA NIM, Gemini, and Local)
# -----------------------------------------------------------------------------

def _call_groq_llama(customer_name: str, address: str, api_key: str) -> dict:
    """Call Groq API (ultra-fast free Llama 3.3 70B / 3.1 8B)."""
    import requests
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    system_prompt = (
        "You are an order quality checker for an Indian D2C e-commerce brand. "
        "Assess the order details and return a JSON object ONLY (no markdown, no extra explanation). "
        "Output format: {\"name_quality\": float 0.0-1.0, \"address_quality\": float 0.0-1.0, \"flags\": [list], \"reasoning\": \"string\"}"
    )
    user_prompt = f"Customer Name: {customer_name}\nDelivery Address: {address}"
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=6)
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    parsed["source"] = "groq-llama-3.3-70b"
    parsed["is_live"] = True
    return parsed


def _call_nvidia_llama(customer_name: str, address: str, api_key: str) -> dict:
    """Call NVIDIA NIM API (Llama 3 / Nemotron)."""
    import requests
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    system_prompt = (
        "You are an order quality checker for an Indian D2C e-commerce brand. "
        "Assess the order details and return a JSON object ONLY (no markdown, no extra explanation). "
        "Output format: {\"name_quality\": float 0.0-1.0, \"address_quality\": float 0.0-1.0, \"flags\": [list], \"reasoning\": \"string\"}"
    )
    user_prompt = f"Customer Name: {customer_name}\nDelivery Address: {address}"

    models = [
        "nvidia/llama-3.1-nemotron-70b-instruct",
        "meta/llama-3.2-11b-vision-instruct",
        "meta/codellama-70b"
    ]
    last_err = None
    for model_name in models:
        try:
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 256
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                raw_text = data["choices"][0]["message"]["content"].strip()
                if "```json" in raw_text:
                    raw_text = raw_text.split("```json")[1].split("```")[0]
                elif "```" in raw_text:
                    raw_text = raw_text.split("```")[1].split("```")[0]
                parsed = json.loads(raw_text.strip())
                parsed["source"] = f"nvidia-{model_name}"
                parsed["is_live"] = True
                return parsed
            else:
                last_err = f"HTTP {resp.status_code}: {resp.text}"
        except Exception as e:
            last_err = str(e)
            continue

    raise RuntimeError(f"All NVIDIA models failed. Last error: {last_err}")


def assess_with_llm(customer_name: str, address: str) -> dict:
    """
    Evaluates order address completeness and customer name validity.
    Supports Groq, NVIDIA NIM, and Google Gemini with graceful fallback.
    """
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    nv_key = os.environ.get("NVIDIA_API_KEY", "").strip() or os.environ.get("NVIDIA_LLAMA_API_KEY", "").strip()
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()

    # 1. Try Groq (if key set)
    if groq_key and groq_key.startswith("gsk_"):
        try:
            return _call_groq_llama(customer_name, address, groq_key)
        except Exception as e:
            return _heuristic_assessment(customer_name, address, error=f"Groq API error: {e}")

    # 2. Try NVIDIA Llama NIM
    active_nv_key = nv_key if nv_key.startswith("nvapi-") else (gemini_key if gemini_key.startswith("nvapi-") else "")
    if active_nv_key:
        try:
            return _call_nvidia_llama(customer_name, address, active_nv_key)
        except Exception as e:
            return _heuristic_assessment(customer_name, address, error=f"NVIDIA API error: {e}")

    # 3. Try Gemini
    if gemini_key and gemini_key.startswith("AIza"):
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-1.5-flash")

            prompt = f"""You are an order quality checker for an Indian D2C e-commerce brand.
Assess the following order details and return a JSON object ONLY (no markdown, no explanation).

Customer Name: {customer_name}
Delivery Address: {address}

Return exactly this JSON:
{{
  "name_quality": <float 0.0-1.0>,
  "address_quality": <float 0.0-1.0>,
  "flags": [<list of issues, empty if none>],
  "reasoning": "<one sentence plain English>"
}}
"""
            response = model.generate_content(prompt)
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            result = json.loads(text.strip())
            result["source"] = "gemini-1.5-flash"
            result["is_live"] = True
            return result
        except Exception as e:
            return _heuristic_assessment(customer_name, address, error=f"Gemini API error: {e}")

    # Default fallback to heuristic NLP
    return _heuristic_assessment(customer_name, address)


def _heuristic_assessment(name: str, address: str, error: str = "") -> dict:
    """Production rule-based fallback when external LLM is offline or unconfigured."""
    import re

    flags = []

    # Name quality heuristic
    name_clean = name.strip().lower()
    fake_name_patterns = [
        r"^(test|asdf|qwerty|xyz|aaa|bbb|abc|na|null|none|unknown)[\s\w]*$",
        r"^[a-z]{1,3}$",
        r"^[\W]+$",
    ]
    name_fake = any(re.match(p, name_clean) for p in fake_name_patterns)
    name_short = len(name_clean.replace(" ", "")) < 4
    name_quality = 0.05 if name_fake else (0.4 if name_short else 0.85)
    if name_fake:
        flags.append("fake_name")

    # Address quality heuristic
    addr_clean = address.strip().lower()
    gibberish_addr = len(addr_clean) < 6 or re.match(r"^[a-z]{1,5}$", addr_clean)
    incomplete = len(addr_clean) < 20 and not any(
        kw in addr_clean for kw in ["road", "nagar", "colony", "street", "lane", "sector", "marg", "gali", "mohalla"]
    )
    hinglish = any(kw in addr_clean for kw in ["gali", "saamne", "paas", "wala", "wali", "ke", "ka", "ki", "pe", "pr"])

    if gibberish_addr:
        address_quality = 0.05
        flags.append("gibberish_address")
    elif incomplete:
        address_quality = 0.35
        flags.append("incomplete_address")
    elif hinglish:
        address_quality = 0.65
        flags.append("hinglish_address")
    else:
        address_quality = 0.85

    if flags:
        clean_flags = [f.replace("_", " ").title() for f in flags]
        reasoning = f"Heuristic analysis detected potential flags: {', '.join(clean_flags)}."
    else:
        reasoning = "Heuristic address and customer name analysis verified. Standard delivery profile."

    return {
        "name_quality": name_quality,
        "address_quality": address_quality,
        "flags": flags,
        "reasoning": reasoning,
        "source": "heuristic",
        "is_live": False,
        "api_error": error
    }


# -----------------------------------------------------------------------------
# Mathematical Scoring Engine
# -----------------------------------------------------------------------------

def compute_risk_score(order: OrderInput, llm_result: dict, config: dict) -> tuple[float, dict]:
    """
    Compute weighted risk score. Returns (score, breakdown).
    Score is 0.0 (no risk) to 1.0 (certain RTO).
    Pure math — zero LLM calls here.
    """
    weights = config["scoring_weights"]
    hard = config["hard_rules"]

    # 1. Address quality (from LLM/heuristic)
    addr_quality = llm_result.get("address_quality", 0.5)
    addr_risk = 1.0 - addr_quality

    # 2. Pincode historical RTO rate
    pincode_risk = order.pincode_historical_rto_rate

    # 3. Customer history risk
    total = max(order.customer_total_orders, 1)
    rto_rate = order.customer_previous_rto_count / total
    customer_risk = rto_rate

    # 4. First order penalty
    first_order_risk = 1.0 if order.is_first_order else 0.2

    # 5. Order value factor
    order_value_risk = 0.3 if order.order_value > 800 else 0.5

    # 6. Name quality
    name_quality = llm_result.get("name_quality", 0.7)
    name_risk = 1.0 - name_quality

    # Weighted score
    raw_score = (
        weights["address_quality"] * addr_risk +
        weights["pincode_rto_rate"] * pincode_risk +
        weights["customer_history"] * customer_risk +
        weights["first_order_penalty"] * first_order_risk +
        weights["order_value_factor"] * order_value_risk +
        weights["name_quality"] * name_risk
    )

    breakdown = {
        "address_risk": round(addr_risk, 3),
        "pincode_rto_rate": round(pincode_risk, 3),
        "customer_history_rto_rate": round(customer_risk, 3),
        "first_order_risk": round(first_order_risk, 3),
        "order_value_risk": round(order_value_risk, 3),
        "name_risk": round(name_risk, 3),
        "weighted_raw_score": round(raw_score, 3),
    }

    # Hard rule boosts
    boost = 0.0
    if rto_rate > hard["customer_rto_rate_above"]:
        boost += 0.20
        breakdown["boost_high_customer_rto"] = 0.20
    if order.pincode_historical_rto_rate > hard["pincode_rto_rate_above"]:
        boost += 0.15
        breakdown["boost_high_pincode_rto"] = 0.15

    # Absolute overrides for gibberish
    flags = llm_result.get("flags", [])
    if "fake_name" in flags or "gibberish_name" in flags:
        raw_score = max(raw_score, hard["gibberish_name_score"])
        breakdown["override_gibberish_name"] = hard["gibberish_name_score"]
    if "gibberish_address" in flags:
        raw_score = max(raw_score, hard["gibberish_address_score"])
        breakdown["override_gibberish_address"] = hard["gibberish_address_score"]

    final_score = min(raw_score + boost, 1.0)
    breakdown["final_score"] = round(final_score, 3)

    return final_score, breakdown


# -----------------------------------------------------------------------------
# Plain-English Ops Reason Generator
# -----------------------------------------------------------------------------

def generate_reason(action: Action, score: float, breakdown: dict, llm_result: dict, order: OrderInput) -> str:
    """Generate a plain-English reason an ops person can understand."""
    flags = llm_result.get("flags", [])
    reasons = []

    if "fake_name" in flags or "gibberish_name" in flags:
        reasons.append("customer name looks fake or test-like")
    if "gibberish_address" in flags:
        reasons.append("delivery address is undeliverable (gibberish/blank)")
    elif "incomplete_address" in flags:
        reasons.append("address is incomplete (missing area/landmark)")
    elif "hinglish_address" in flags:
        reasons.append("address is in Hinglish — may cause delivery confusion")

    if order.pincode_historical_rto_rate > 0.40:
        reasons.append(f"pincode {order.pincode} has {order.pincode_historical_rto_rate:.0%} historical RTO rate")

    if order.customer_previous_rto_count > 0:
        rto_rate = order.customer_previous_rto_count / max(order.customer_total_orders, 1)
        reasons.append(f"customer has {order.customer_previous_rto_count} previous RTO(s) ({rto_rate:.0%} rate)")

    if order.is_first_order:
        reasons.append("first-time customer (higher baseline risk)")

    if not reasons:
        if score < 0.25:
            reasons.append("known address, repeat customer with clean delivery history")
        else:
            reasons.append(f"combined risk score {score:.2f} based on address, pincode, and customer history")

    reason_text = "; ".join(reasons).capitalize() + "."

    action_suffix = {
        Action.SHIP_AS_IS: " Low risk — proceed with dispatch.",
        Action.NUDGE_TO_PREPAID: " Offer ₹30 discount to switch to prepaid.",
        Action.SHIP_AFTER_CONFIRMATION: " Request WhatsApp confirmation before shipping.",
        Action.HOLD_CANCEL: " Hold order and flag for manual review or cancellation.",
    }

    return reason_text + action_suffix[action]


# -----------------------------------------------------------------------------
# Main Decision Function
# -----------------------------------------------------------------------------

def decide(order: OrderInput, config: dict = None, use_llm: bool = True) -> DecisionOutput:
    """
    Main entry point. Given an order, return a DecisionOutput with action + reason.
    """
    if config is None:
        config = load_config()

    thresholds = config["risk_thresholds"]

    # Step 1: LLM assessment (address + name quality)
    if use_llm:
        llm_result = assess_with_llm(order.customer_name, order.address)
    else:
        llm_result = _heuristic_assessment(order.customer_name, order.address)

    llm_used = bool(llm_result.get("is_live", False))

    # Step 2: Compute risk score (pure math)
    score, breakdown = compute_risk_score(order, llm_result, config)

    # Step 3: Apply thresholds to pick action
    if score <= thresholds["ship_as_is_max"]:
        action = Action.SHIP_AS_IS
    elif score <= thresholds["nudge_to_prepaid_max"]:
        action = Action.NUDGE_TO_PREPAID
    elif score <= thresholds["confirm_before_ship_max"]:
        action = Action.SHIP_AFTER_CONFIRMATION
    else:
        action = Action.HOLD_CANCEL

    # Step 4: Generate reason
    reason = generate_reason(action, score, breakdown, llm_result, order)

    return DecisionOutput(
        order_id=order.order_id,
        action=action,
        risk_score=round(score, 4),
        reason=reason,
        score_breakdown=breakdown,
        llm_used=llm_used,
        llm_flags={"flags": llm_result.get("flags", []), "reasoning": llm_result.get("reasoning", "")},
    )


def process_batch(orders: list[OrderInput], config: dict = None, use_llm: bool = True) -> list[DecisionOutput]:
    """Process a list of orders. Useful for dashboard/batch runs."""
    if config is None:
        config = load_config()
    return [decide(order, config, use_llm) for order in orders]
