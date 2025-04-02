from pydantic_ai import Agent, RunContext
from typing import List, Dict, Optional
from dataclasses import dataclass
import logfire
import json
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import get_model

logfire.configure(send_to_logfire='if-token-present')

model = get_model()

@dataclass
class HotelDeps:
    hotel_amenities: List[str]
    budget_levl: str

system_prompt= """
You are a hotel specialist who helps users find the best accommodations for their trips.

Use the search_hotels tool to find hotel options and then provide personalized recommendations 
based on the user's preferences (location, amenities, price range).

The user's preferences are available in the context, including preferred amenities and budget level.

Always explain the reasoning behind your choice and recommendations.

Format your response in a clear, organised way with hotel details, amenities and prices.

Never ask for clarification on any piece of information before recommending hotels, just make the 
best guess for any parameters that you are not sure of.
"""

hotel_agent = Agent(
    model,
    system_prompt=system_prompt,
    deps_type=HotelDeps,
    retries=2
)

@hotel_agent.tool
async def search_hotels(ctx: RunContext[HotelDeps], city: str, check_out: str, max_price: Optional[float] = None) -> str:
    """Search for hotels in a city for specific dates within a price range, taking user preference into account."""

    # Use hard-coded data for now.
    hotel_options = [
        {
            "name": "City Center Hotel",
            "location": "Downtown",
            "price_per_night": 199.99,
            "amenities": ["WiFi", "Pool", "Gym", "Restaurant"]
        },
        {
            "name": "Riverside Inn",
            "location": "Riverside District",
            "price_per_night": 149.50,
            "amenities": ["WiFi", "Free Breakfast", "Parking"]
        },
        {
            "name": "Luxury Palace",
            "location": "Historic District",
            "price_per_night": 349.99,
            "amenities": ["WiFi", "Pool", "Spa", "Fine Dining", "Concierge"]
        }
    ]

    # Filter by max price if required
    if max_price is not None:
        filtered_hotels = [hotel for hotel in hotel_options if hotel["price_per_night"]<=max_price]
    else:
        filtered_hotels = hotel_options

    # Now check for user preferences
    preferred_amenities = ctx.deps.hotel_amenities
    budget_level = ctx.deps.budget_levl

    if preferred_amenities is not None:
        # Get a score for each hotel based on matching amenities
        for hotel in filtered_hotels:
            matching_amenties = [amenity for amenity in hotel["amenities"] if amenity in preferred_amenities]
            hotel["preference_score"] = len(matching_amenties)

        # sort based on preference score
        filtered_hotels.sort(key = lambda x: x["preference_score"], reverse=True)

    if budget_level is not None:
        if budget_level == "budget":
            filtered_hotels.sort(key= lambda x: x["price_per_night"])

        elif budget_level == "luxury":
            filtered_hotels.sort(key= lambda x: x["price_per_night"], reverse=True)

    return json.dumps(filtered_hotels)