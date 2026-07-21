#!/usr/bin/env python3
"""Non-interactive entry point for gateway-triggered conversational form-
fill — the WhatsApp-facing sibling of `whatsapp_intake_handler.py` (that
one's for inbound document photos; this one's for a client working through
an intake form one question at a time).

Called by OpenClaw's own agent exec tool once per inbound message, same
convention as `whatsapp_intake_handler.py`: two positional args in, a reply
string out on stdout for the calling agent to relay back over WhatsApp.
All the actual logic — question schemas, state, validation, case creation —
lives in `intake_form_fill/handler.py`; this file is just the wiring that
puts it at the path OpenClaw is configured to call.

Usage: python3 whatsapp_form_fill_handler.py "<phone number>" "<message text>"
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "intake_form_fill"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))

from handler import handle_message


def main() -> None:
    if len(sys.argv) < 3:
        print("Sorry, I couldn't process that — could you try again?")
        return
    phone, message = sys.argv[1], sys.argv[2]
    print(handle_message(phone, message))


if __name__ == "__main__":
    main()
