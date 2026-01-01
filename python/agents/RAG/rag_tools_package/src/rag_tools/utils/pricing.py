
PRICING_TABLE = {
    "gemini-3-pro-preview": {
        "input": {
            "standard": 2.00,  # <= 200k
            "long": 4.00       # > 200k
        },
        "output": {
            "standard": 12.00, # <= 200k
            "long": 18.00      # > 200k
        }
    },
    "gemini-3-flash-preview": {
        "input": {
            "standard": 0.50,
            "long": 0.50
        },
        "output": {
            "standard": 3.00,
            "long": 3.00
        }
    },
    "gemini-2.5-pro": {
        "input": {
            "standard": 1.25,
            "long": 2.50
        },
        "output": {
            "standard": 10.00,
            "long": 15.00
        }
    },
    "gemini-2.5-flash": {
        "input": {
            "standard": 0.30,
            "long": 0.30
        },
        "output": {
            "standard": 2.50,
            "long": 2.50
        }
    }
}

def calculate_cost(model_id, prompt_tokens, candidate_tokens):
    """
    Calculates the estimated cost for a generation request.
    Returns the cost in USD.
    """
    # Normalize model ID (handle versions or slight variations if needed)
    # For now, exact match or fallback
    pricing = PRICING_TABLE.get(model_id)
    
    if not pricing:
        # Try to find a partial match (e.g. "gemini-1.5-pro-001" -> "gemini-1.5-pro")
        for key in PRICING_TABLE:
            if key in model_id:
                pricing = PRICING_TABLE[key]
                break
    
    if not pricing:
        return 0.0

    # Determine tier based on prompt length (context window)
    # Note: The pricing tier usually depends on the *prompt* length for input pricing,
    # and sometimes the prompt length also dictates the output pricing tier (like in 1.5 Pro).
    # For Gemini 3 Pro, the table says "prompts <= 200k" vs "> 200k".
    
    is_long_context = prompt_tokens > 200000
    tier = "long" if is_long_context else "standard"

    input_price_per_1m = pricing["input"][tier]
    output_price_per_1m = pricing["output"][tier]

    input_cost = (prompt_tokens / 1_000_000) * input_price_per_1m
    output_cost = (candidate_tokens / 1_000_000) * output_price_per_1m

    return input_cost + output_cost
