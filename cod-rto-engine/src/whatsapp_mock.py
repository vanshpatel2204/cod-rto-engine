"""
WhatsApp Confirmation & AI Interaction Engine
Oytra COD RTO Prevention & Customer Conversational Mock
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from enum import Enum
import re
import json


class ReplyType(str, Enum):
    YES = "yes"
    NO = "no"
    RANDOM = "random"
    NO_REPLY = "no_reply"


class FlowType(str, Enum):
    CONFIRM_BEFORE_SHIP = "confirm_before_ship"
    NUDGE_TO_PREPAID = "nudge_to_prepaid"


@dataclass
class Message:
    sender: str          # "system" or "customer"
    text: str
    timestamp: datetime
    message_type: str    # "outbound" | "inbound" | "system_action"


@dataclass
class FlowResult:
    order_id: str
    flow_type: FlowType
    final_action: str    # "ship", "cancel", "converted_to_prepaid", "timed_out"
    messages: list[Message] = field(default_factory=list)
    converted: bool = False
    revenue_impact_inr: float = 0.0
    notes: str = ""


# -----------------------------------------------------------------------------
# Message Templates (Clean UTF-8, Hinglish & English)
# -----------------------------------------------------------------------------

def get_confirmation_message(order_id: str, order_value: float, items: str, language: str = "en") -> str:
    if language == "hinglish":
        return (
            f"Namaste! 👋 Aapka order *#{order_id}* (₹{order_value:.0f} — {items}) dispatch ke liye pack ho chuka hai.\n\n"
            f"Delivery confirm karne ke liye kripya reply karein:\n"
            f"✅ *YES* — Mera order bhej dijiye\n"
            f"❌ *NO* — Order cancel karein\n\n"
            f"⏳ 24 ghante mein reply na aane par order hold par chala jayega."
        )
    return (
        f"Hi! 👋 Your order *#{order_id}* for *₹{order_value:.0f}* ({items}) is packed and ready to ship.\n\n"
        f"To confirm your Cash on Delivery shipment, please reply:\n"
        f"✅ *YES* — Ship my order\n"
        f"❌ *NO* — Cancel my order\n\n"
        f"⏳ We hold unconfirmed COD orders for 24 hours before holding dispatch."
    )


def get_prepaid_nudge_message(order_id: str, order_value: float, discount: int, discount_code: str, language: str = "en") -> str:
    discounted = max(0.0, float(order_value) - float(discount))
    if language == "hinglish":
        return (
            f"Namaste! 👋 Aapke order *#{order_id}* par ek special offer hai!\n\n"
            f"🎉 *Online pay karein aur ₹{discount} bachayein!*\n"
            f"Aapka total: ~₹{order_value:.0f}~ ➔ *₹{discounted:.0f}*\n"
            f"Coupon code: *{discount_code}*\n\n"
            f"Secure UPI payment link pane ke liye *YES* reply karein, ya COD rakhne ke liye *NO* reply karein.\n"
            f"⚡ Offer agle 24 ghante ke liye valid hai."
        )
    return (
        f"Hi! 👋 Your order *#{order_id}* (₹{order_value:.0f}) is being prepped for dispatch.\n\n"
        f"🎉 *Limited Prepaid Offer:* Pay online now and save *₹{discount}* instantly!\n"
        f"Final amount: ~₹{order_value:.0f}~ ➔ *₹{discounted:.0f}*\n"
        f"Discount code applied: *{discount_code}*\n\n"
        f"Reply *YES* to receive your 1-click UPI/Card payment link, or *NO* to continue with COD.\n"
        f"⚡ Offer expires in 24 hours."
    )


def get_payment_link_message(discount_code: str, discounted_amount: float, language: str = "en") -> str:
    if language == "hinglish":
        return (
            f"Badhiya! 💳 Yeh raha aapka secure UPI/Card payment link:\n"
            f"🔗 https://pay.oytra.in/checkout?code={discount_code}\n"
            f"Payable amount: *₹{discounted_amount:.0f}*\n\n"
            f"⏱️ Offer lock karne ke liye agle 2 ghante mein payment complete karein."
        )
    return (
        f"Great choice! 💳 Here is your secure instant payment link:\n"
        f"🔗 https://pay.oytra.in/checkout?code={discount_code}\n"
        f"Amount payable: *₹{discounted_amount:.0f}*\n\n"
        f"⏱️ Complete payment within 2 hours to secure your ₹30 savings and fast-track shipping."
    )


def get_no_reply_message(language: str = "en") -> str:
    if language == "hinglish":
        return (
            "⏳ 24 ghante beet chuke hain aur humein aapka reply nahi mila.\n"
            "Aapka order suraksha ke liye *Hold* par rakh diya gaya hai. Reactivate karne ke liye yahan *YES* reply karein ya oytra.in par visit karein."
        )
    return (
        "⏳ We haven't heard back from you in 24 hours.\n"
        "Your order has been temporarily placed on *HOLD* to prevent unintended delivery. Reply *YES* anytime to resume shipment."
    )


def get_random_reply_clarification(language: str = "en") -> str:
    if language == "hinglish":
        return (
            "Kshama karein, hum samajh nahi paaye! 🤔\n"
            "Kripya keval yeh reply karein:\n"
            "✅ *YES* — Order confirm karne ke liye\n"
            "❌ *NO* — Order cancel karne ke liye"
        )
    return (
        "Sorry, we didn't quite catch that! 🤔\n"
        "Please reply with one of the following:\n"
        "✅ *YES* — to confirm and ship\n"
        "❌ *NO* — to cancel your order"
    )


# -----------------------------------------------------------------------------
# Standard Flow Simulators
# -----------------------------------------------------------------------------

def simulate_confirmation_flow(
    order_id: str,
    order_value: float,
    items: str,
    reply_type: ReplyType,
    no_reply_action: str = "hold_cancel",
    language: str = "en",
) -> FlowResult:
    """Simulate the 'Ship after confirmation' WhatsApp flow."""
    messages = []
    now = datetime.now()

    msg1 = get_confirmation_message(order_id, order_value, items, language=language)
    messages.append(Message("system", msg1, now, "outbound"))

    if reply_type == ReplyType.YES:
        messages.append(Message("customer", "YES", now + timedelta(minutes=14), "inbound"))
        ack = (
            f"✅ Shandar! Order #{order_id} confirm ho gaya hai. Hum aaj hi dispatch kar rahe hain. Tracking: oytra.in/track/{order_id}"
            if language == "hinglish"
            else f"✅ Confirmed! Your order #{order_id} has been prioritized for dispatch. Tracking details: oytra.in/track/{order_id}"
        )
        messages.append(Message("system", ack, now + timedelta(minutes=15), "outbound"))
        return FlowResult(
            order_id=order_id,
            flow_type=FlowType.CONFIRM_BEFORE_SHIP,
            final_action="ship",
            messages=messages,
            converted=False,
            revenue_impact_inr=0.0,
            notes="Customer explicitly confirmed delivery intent via WhatsApp. Safe to ship COD."
        )

    elif reply_type == ReplyType.NO:
        messages.append(Message("customer", "NO", now + timedelta(minutes=45), "inbound"))
        cancel_ack = (
            f"❌ Order #{order_id} cancel kar diya gaya hai. Koi charges nahi liye gaye. Phir milenge!"
            if language == "hinglish"
            else f"❌ Order #{order_id} has been cancelled per your request. No payment was charged. Hope to serve you soon!"
        )
        messages.append(Message("system", cancel_ack, now + timedelta(minutes=46), "outbound"))
        messages.append(Message("system", f"🛡️ RTO Avoided! Saved ₹169 in shipping & packaging costs.", now + timedelta(minutes=46), "system_action"))
        return FlowResult(
            order_id=order_id,
            flow_type=FlowType.CONFIRM_BEFORE_SHIP,
            final_action="cancel",
            messages=messages,
            revenue_impact_inr=-round(float(order_value) * 0.62, 2),
            notes="Customer declined order prior to dispatch. Avoided ₹169.40 RTO courier cost."
        )

    elif reply_type == ReplyType.RANDOM:
        cust_msg = "konsa item hai ye? maine kab mangwaya?" if language == "hinglish" else "Wait what is this? I don't remember"
        messages.append(Message("customer", cust_msg, now + timedelta(hours=1, minutes=12), "inbound"))
        clarification = get_random_reply_clarification(language=language)
        messages.append(Message("system", clarification, now + timedelta(hours=1, minutes=13), "outbound"))
        messages.append(Message("customer", "YES", now + timedelta(hours=2), "inbound"))
        final_ack = (
            f"✅ Samajh gaye! Order #{order_id} pack karke bhej rahe hain."
            if language == "hinglish"
            else f"✅ Thank you for confirming! Order #{order_id} is on its way."
        )
        messages.append(Message("system", final_ack, now + timedelta(hours=2, minutes=1), "outbound"))
        return FlowResult(
            order_id=order_id,
            flow_type=FlowType.CONFIRM_BEFORE_SHIP,
            final_action="ship",
            messages=messages,
            notes="Customer had initial doubt, resolved via clarification prompt and successfully confirmed."
        )

    else:  # NO_REPLY
        messages.append(Message("system", get_no_reply_message(language=language), now + timedelta(hours=24), "outbound"))
        messages.append(Message("system", f"⚙️ Automated webhook: Order #{order_id} tagged '{no_reply_action}' in Shopify ERP after 24h timeout.", now + timedelta(hours=24, minutes=1), "system_action"))
        return FlowResult(
            order_id=order_id,
            flow_type=FlowType.CONFIRM_BEFORE_SHIP,
            final_action=no_reply_action,
            messages=messages,
            revenue_impact_inr=-round(float(order_value) * 0.62, 2) if no_reply_action == "hold_cancel" else 0.0,
            notes=f"Zero customer response within 24h SLA. Order placed on {no_reply_action} to prevent dead freight."
        )


def simulate_prepaid_nudge_flow(
    order_id: str,
    order_value: float,
    items: str,
    discount: int,
    discount_code: str,
    reply_type: ReplyType,
    language: str = "en",
) -> FlowResult:
    """Simulate the 'Nudge to prepaid' WhatsApp flow."""
    messages = []
    now = datetime.now()
    discounted = max(0.0, float(order_value) - float(discount))

    msg1 = get_prepaid_nudge_message(order_id, order_value, discount, discount_code, language=language)
    messages.append(Message("system", msg1, now, "outbound"))

    if reply_type == ReplyType.YES:
        messages.append(Message("customer", "YES", now + timedelta(minutes=22), "inbound"))
        messages.append(Message("system", get_payment_link_message(discount_code, discounted, language=language), now + timedelta(minutes=23), "outbound"))
        messages.append(Message("customer", "Done payment via GPay 💳", now + timedelta(minutes=29), "inbound"))
        success_ack = (
            f"🎉 Payment mila! ₹{discounted:.0f} successfully received. Aapka prepaid order #{order_id} express delivery se dispatch hoga."
            if language == "hinglish"
            else f"🎉 Payment Verified! ₹{discounted:.0f} received via Razorpay UPI. Order #{order_id} upgraded to Priority Shipping."
        )
        messages.append(Message("system", success_ack, now + timedelta(minutes=30), "outbound"))
        messages.append(Message("system", f"⚡ Converted COD ➔ Prepaid! RTO risk collapsed from 28% to 4%.", now + timedelta(minutes=30), "system_action"))

        rto_saving = (0.28 - 0.04) * (65 + 65 + 25 + 0.08 * 180)
        net_gain = rto_saving - discount
        return FlowResult(
            order_id=order_id,
            flow_type=FlowType.NUDGE_TO_PREPAID,
            final_action="converted_to_prepaid",
            messages=messages,
            converted=True,
            revenue_impact_inr=round(net_gain, 2),
            notes=f"Customer converted from COD to Prepaid with ₹{discount} discount. Net saving: ₹{net_gain:.1f}."
        )

    elif reply_type == ReplyType.NO:
        messages.append(Message("customer", "NO", now + timedelta(minutes=35), "inbound"))
        cod_ack = (
            f"Koi baat nahi! Order #{order_id} Cash on Delivery se hi aayega. Delivery boy ko exact ₹{order_value:.0f} cash ya UPI se pay kar sakte hain."
            if language == "hinglish"
            else f"Understood! Order #{order_id} will be delivered as standard Cash on Delivery for ₹{order_value:.0f}. Cash or UPI accepted on delivery."
        )
        messages.append(Message("system", cod_ack, now + timedelta(minutes=36), "outbound"))
        messages.append(Message("system", f"ℹ️ Customer opted to keep COD. Normal dispatch path scheduled.", now + timedelta(minutes=36), "system_action"))
        return FlowResult(
            order_id=order_id,
            flow_type=FlowType.NUDGE_TO_PREPAID,
            final_action="ship_cod",
            messages=messages,
            converted=False,
            revenue_impact_inr=0.0,
            notes="Customer declined prepaid incentive; kept standard COD. Standard risk applies."
        )

    elif reply_type == ReplyType.RANDOM:
        cust_msg = "is payment link safe?" if language == "hinglish" else "Is this payment link authentic?"
        messages.append(Message("customer", cust_msg, now + timedelta(minutes=18), "inbound"))
        clarify = (
            f"Ji bilkul! 🔒 Yeh Razorpay 256-bit encrypted link hai. ₹{discount} discount ke sath aapka final amount ₹{discounted:.0f} hai.\nLink: https://pay.oytra.in/checkout?code={discount_code}"
            if language == "hinglish"
            else f"Yes, 100% secure! 🔒 Powered by Razorpay with 256-bit SSL encryption. Final payable with ₹{discount} discount: ₹{discounted:.0f}.\nLink: https://pay.oytra.in/checkout?code={discount_code}"
        )
        messages.append(Message("system", clarify, now + timedelta(minutes=19), "outbound"))
        messages.append(Message("customer", "Paid! Thank you", now + timedelta(minutes=28), "inbound"))
        messages.append(Message("system", f"🎉 Payment received! Order #{order_id} marked as Priority Dispatch.", now + timedelta(minutes=29), "outbound"))
        messages.append(Message("system", f"⚡ Converted COD ➔ Prepaid after security reassurance.", now + timedelta(minutes=29), "system_action"))

        rto_saving = (0.28 - 0.04) * (65 + 65 + 25 + 0.08 * 180)
        net_gain = rto_saving - discount
        return FlowResult(
            order_id=order_id,
            flow_type=FlowType.NUDGE_TO_PREPAID,
            final_action="converted_to_prepaid",
            messages=messages,
            converted=True,
            revenue_impact_inr=round(net_gain, 2),
            notes="Security query addressed; converted to prepaid successfully."
        )

    else:  # NO_REPLY
        messages.append(Message("system", f"⏱️ Prepaid discount offer expired for order #{order_id}. Proceeding with standard COD dispatch.", now + timedelta(hours=24), "outbound"))
        messages.append(Message("system", f"ℹ️ Timeout (24h) reached. Standard COD dispatch initiated.", now + timedelta(hours=24, minutes=1), "system_action"))
        return FlowResult(
            order_id=order_id,
            flow_type=FlowType.NUDGE_TO_PREPAID,
            final_action="ship_cod_no_reply",
            messages=messages,
            converted=False,
            revenue_impact_inr=0.0,
            notes="No response to prepaid nudge within 24h. Order dispatched via standard COD."
        )


# -----------------------------------------------------------------------------
# AI Conversational Intent & Response Engine
# -----------------------------------------------------------------------------

def generate_ai_chat_response(
    order_id: str,
    order_value: float,
    items: str,
    flow_type: str,
    customer_message: str,
    discount: int = 30,
    language: str = "en",
) -> tuple[str, str, str, dict]:
    """
    Intelligent Conversational AI agent for customer questions.
    Returns: (bot_reply, intent, ops_action, meta)
    """
    c_lower = customer_message.strip().lower()

    meta = {"is_live": True, "provider": "Oytra AI Assistant", "model": "conversational-intent-v2.4"}

    # 1. RETURN / REFUND / REPLACEMENT POLICY
    if any(k in c_lower for k in ["return", "refund", "exchange", "policy", "guarantee", "damaged", "replacement", "wapas", "kharab", "toot", "badla"]):
        if language == "hinglish":
            reply = (
                f"Ji bilkul! 🛡️ Oytra par 7 days ki easy doorstep replacement aur return policy hai agar delivery ke waqt item damaged ya defective nikle.\n"
                f"Aap bilkul befikr hokar order le sakte hain! Kya hum order #{order_id} dispatch karein? (Reply *YES* ya *NO*)"
            )
        else:
            reply = (
                f"Yes, absolutely! 🛡️ Oytra offers a 7-day hassle-free doorstep replacement or return if the product is damaged or defective upon delivery.\n"
                f"You can shop with total confidence! Shall we proceed with dispatching order #{order_id}? (Reply *YES* or *NO*)"
            )
        return reply, "inquiry", "Customer inquired about return/replacement policy. 7-day policy confirmed; confirmation pending.", meta

    # 2. DELIVERY TIMING / TIME SLOT / SCHEDULING (e.g. '5 baje ke baad deliver ho sakta hai kya?')
    elif any(k in c_lower for k in ["5 baje", "baje", "time", "timing", "deliver", "kab", "when", "evening", "morning", "sunday", "slot", "call"]):
        if language == "hinglish":
            reply = (
                f"Ji bilkul bhaiya! 🚚 Humne aapke order #{order_id} par special delivery instruction add kar diya hai ki delivery boy sham ko call karke aapke bataye time par attempt kare.\n"
                f"Delivery se pehle executive aapko zaroor call karega. Kya dispatch confirm karein? (Reply *YES* ya *NO*)"
            )
        else:
            reply = (
                f"Yes, absolutely! 🚚 We have added a priority delivery note for our courier partner to attempt delivery per your preferred time slot.\n"
                f"The delivery executive will call you prior to arrival. Shall we proceed with dispatch for order #{order_id}? (Reply *YES* or *NO*)"
            )
        return reply, "inquiry", "Customer requested delivery timing adjustment. Instruction noted; confirmation pending.", meta

    # 3. IDENTITY / WHO ARE YOU / BOT QUESTIONS
    elif re.search(r"\b(who are you|who is this|kaun ho|aap kaun|koun|bot|ai|human|real person|robot)\b", c_lower):
        if language == "hinglish":
            reply = (
                f"Namaste! 👋 Main Oytra ka automated WhatsApp customer concierge hoon.\n"
                f"Main aapke order #{order_id} ({items}) ke dispatch confirmation aur questions mein help karne ke liye hoon. Kya order dispatch karein? (Reply *YES* ya *NO*)"
            )
        else:
            reply = (
                f"Hello! 👋 I am Oytra's automated WhatsApp support assistant.\n"
                f"I'm here to assist with confirming your order #{order_id} ({items}) and answering any delivery, return, or payment questions! Ready to ship? (Reply *YES* or *NO*)"
            )
        return reply, "inquiry", "Bot identity explained. Awaiting customer confirmation.", meta

    # 4. PRODUCT / INGREDIENTS / HAIR CONCERNS / SAFETY
    elif any(k in c_lower for k in ["ingredient", "dandruff", "hair fall", "sulfate", "paraben", "how to use", "safe", "side effect", "kaise use", "result", "oil", "serum", "hair mask", "color"]):
        if language == "hinglish":
            reply = (
                f"Oytra Anti-Dandruff Hair Mask 100% sulfate & paraben-free hai! 🌿 Isme Salicylic Acid & Tea Tree Oil hai jo scalp dandruff ko jad se clear karta hai bina baal dry kiye.\n"
                f"Shampoo ke baad 10-15 min lagakar dho lijiye. Kya order #{order_id} dispatch confirm karein? (Reply *YES* ya *NO*)"
            )
        else:
            reply = (
                f"Oytra's Anti-Dandruff Mask is 100% sulfate & paraben-free! 🌿 Formulated with Salicylic Acid & Tea Tree Oil to gently purify the scalp without stripping natural oils.\n"
                f"Use 2-3 times weekly after shampooing. Shall we prioritize dispatch for order #{order_id}? (Reply *YES* or *NO*)"
            )
        return reply, "inquiry", "Product ingredients and safety details shared. Awaiting confirmation.", meta

    # 5. PAYMENT / UPI / ONLINE / PREPAID DISCOUNT
    elif any(k in c_lower for k in ["pay", "payment", "online", "upi", "discount", "link", "gpay", "phonepe", "paytm", "card", "prepaid"]):
        disc_val = max(0.0, float(order_value) - float(discount))
        if language == "hinglish":
            reply = (
                f"Aap delivery par Cash ya UPI (GPay/PhonePe) dono se de sakte hain! 💵\n"
                f"💳 Lekin agar abhi online pay karenge toh ₹{discount} ka instant discount milega: https://pay.oytra.in/checkout?code=PAYNOW{order_id[-4:]}\n"
                f"Aapko sirf *₹{disc_val:.0f}* pay karna hoga."
            )
        else:
            reply = (
                f"You can pay via Cash or UPI at doorstep! 💵\n"
                f"💳 Or pay online now to receive an instant ₹{discount} discount: https://pay.oytra.in/checkout?code=PAYNOW{order_id[-4:]}\n"
                f"Final payable amount: *₹{disc_val:.0f}*."
            )
        return reply, "prepaid", f"Prepaid payment link sent with ₹{discount} discount. Payable: ₹{disc_val:.0f}.", meta

    # 6. ADDRESS CORRECTION
    elif any(k in c_lower for k in ["address", "pata", "change", "galat", "wrong", "location", "flat", "street", "house", "colony", "pincode"]):
        if language == "hinglish":
            reply = (
                f"Koi baat nahi! 📍 Kripya apna sahi delivery address yahan reply karein.\n"
                f"Hum order #{order_id} dispatch karne se pehle shipping label par update kar denge."
            )
        else:
            reply = (
                f"No worries at all! 📍 Please reply with your updated address right here.\n"
                f"We will update the shipping label for order #{order_id} before it leaves our warehouse."
            )
        return reply, "inquiry", "Customer requested address modification. Awaiting new address details.", meta

    # 7. ORDER DETAILS / WHAT IS THIS
    elif any(k in c_lower for k in ["kya hai", "item", "product", "konsa", "what is", "details", "kya mangwaya"]):
        if language == "hinglish":
            reply = (
                f"Aapka order #{order_id} *{items}* ke liye hai, jiska total amount *₹{order_value:.0f}* hai. ✨\n"
                f"Kya aap delivery confirm karna chahte hain? (Reply *YES* ya *NO*)"
            )
        else:
            reply = (
                f"Your order #{order_id} contains: *{items}* for a total of *₹{order_value:.0f}*. ✨\n"
                f"Would you like us to confirm and dispatch your order? (Reply *YES* or *NO*)"
            )
        return reply, "inquiry", "Customer asked about order contents. Details shared; awaiting confirmation.", meta

    # 8. CANCELLATION REQUESTS
    elif any(k in c_lower for k in ["cancel", "cancle", "nahi chahiye", "dont want", "mat bhej", "stop"]) or re.search(r"\b(no|nhi|nahi)\b", c_lower):
        if language == "hinglish":
            reply = f"❌ Samajh gaye! Order #{order_id} cancel kar diya gaya hai. Koi charges nahi liye gaye. Oytra par shopping karne ke liye shukriya!"
        else:
            reply = f"❌ Understood! Order #{order_id} has been successfully cancelled. Zero charges incurred. Hope to see you again soon!"
        return reply, "cancel", f"Order #{order_id} cancelled by customer. Saved ₹169 forward & reverse freight.", meta

    # 9. CONFIRMATION RESPONSES
    elif any(k in c_lower for k in ["bhej do", "confirm", "ship", "send", "deliver it"]) or re.search(r"\b(yes|ha|haan|haa|ok|okay|sure)\b", c_lower):
        if language == "hinglish":
            reply = f"✅ Shandar! Order #{order_id} confirm ho gaya hai. Hum aaj hi BlueDart/Delhivery se dispatch kar rahe hain. Tracking: oytra.in/track/{order_id}"
        else:
            reply = f"✅ Thank you! Order #{order_id} is confirmed and prioritised for dispatch. Track live at oytra.in/track/{order_id}"
        return reply, "confirm", "Customer confirmed delivery intent. Safe to ship COD.", meta

    # 10. GENERAL INQUIRY FALLBACK
    else:
        if language == "hinglish":
            reply = (
                f"Namaste! 👋 Main Oytra support assistant hoon. Aapke order #{order_id} ({items}) ke baare mein koi bhi sawal ho toh zaroor batayein.\n"
                f"Kya hum aapka shipment dispatch karein? (Reply *YES* ya *NO*)"
            )
        else:
            reply = (
                f"Hi there! 👋 I'm Oytra's support assistant for order #{order_id} ({items}).\n"
                f"Feel free to ask any questions about your delivery, returns, or payment. Shall we proceed with dispatch? (Reply *YES* or *NO*)"
            )
        return reply, "inquiry", "Customer query acknowledged. Awaiting explicit confirmation.", meta


def simulate_custom_ai_flow(
    order_id: str,
    order_value: float,
    items: str,
    flow_type_str: str,
    customer_message: str,
    discount: int = 30,
    language: str = "en"
) -> FlowResult:
    """Simulates a live multi-turn AI chat interaction with a custom customer query."""
    now = datetime.now()
    messages = []

    # 1. Outbound bot message
    if "Confirmation" in flow_type_str:
        outbound = get_confirmation_message(order_id, order_value, items, language=language)
        f_type = FlowType.CONFIRM_BEFORE_SHIP
    else:
        code = f"PAYNOW{order_id[-4:]}"
        outbound = get_prepaid_nudge_message(order_id, order_value, discount, code, language=language)
        f_type = FlowType.NUDGE_TO_PREPAID

    messages.append(Message("system", outbound, now, "outbound"))

    # 2. Inbound customer message
    messages.append(Message("customer", customer_message, now + timedelta(minutes=14), "inbound"))

    # 3. AI Bot response
    bot_reply, intent, ops_action, meta = generate_ai_chat_response(
        order_id, order_value, items, flow_type_str, customer_message, discount=discount, language=language
    )
    messages.append(Message("system", bot_reply, now + timedelta(minutes=15), "outbound"))

    # Audit pill
    if intent == "confirm":
        badge_text = "✅ Confirmed via AI Chat • Priority COD Dispatched"
    elif intent == "cancel":
        badge_text = "🛑 Cancelled via AI Chat • Saved ₹169 Forward & Reverse Freight"
    elif intent == "prepaid":
        badge_text = "💳 Converted to Prepaid via AI Chat • RTO Risk Slashed to 4%"
    else:
        badge_text = "⚙️ AI Assistant Resolved Customer Query • Confirmation Pending"

    messages.append(Message("system", badge_text, now + timedelta(minutes=15), "system_action"))

    if intent == "confirm":
        return FlowResult(order_id, f_type, "ship", messages, False, 0.0, ops_action)
    elif intent == "cancel":
        return FlowResult(order_id, f_type, "cancel", messages, False, -round(float(order_value) * 0.62, 2), ops_action)
    elif intent == "prepaid":
        rto_saving = (0.28 - 0.04) * (65 + 65 + 25 + 0.08 * 180)
        net_gain = rto_saving - discount
        return FlowResult(order_id, f_type, "converted_to_prepaid", messages, True, round(net_gain, 2), ops_action)
    else:
        return FlowResult(order_id, f_type, "ship_after_confirmation", messages, False, 0.0, ops_action)
