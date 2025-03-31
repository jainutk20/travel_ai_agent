from pydantic_ai import Agent, RunContext
from typing import Any, List, Dict
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
class FlightDeps:
    preferred_airlines: List[str]

system_prompt = """
You are a flight specialist who helps users find the best flights for their trips.

Use the search_flights tool to find flight options, and then provide personalized recommendations
based on the user's preference (price, time, direct vs connecting).

The user's preferences are available in the context, including the preferred airlines.

Always explain the reasoning behind your recommendations.

Format your response in a clear, organised way with flight details and prices.

Never ask for clarification on any piece of information before recommending flights, just make the 
best guess for any parameters that you are not sure of.
"""

flight_agent = Agent(
    model=model,
    system_prompt=system_prompt,
    deps_type= FlightDeps,
    retries=2
)

@flight_agent.tool
async def search_flights(ctx: RunContext[FlightDeps], origin:str, destination:str, data: str) -> str:
    """Search for flights between two cities on a specific date, taking user preferences into account."""

    # for now, take this list of flights for each input.
    # TODO: replace this with a real API call
    flight_options= [
        {
            "airline": "SkyWays",
            "departure_time": "08:00",
            "arrival_time": "10:30",
            "price": 350.00,
            "direct": True
        },
        {
            "airline": "OceanAir",
            "departure_time": "12:45",
            "arrival_time": "15:15",
            "price": 275.50,
            "direct": True
        },
        {
            "airline": "MountainJet",
            "departure_time": "16:30",
            "arrival_time": "21:45",
            "price": 225.75,
            "direct": False
        }
    ]
    # if the user prefers certain airlines, sort based on that.
    if ctx.deps.preferred_airlines:
        preferred_airlines = ctx.deps.preferred_airlines
        if preferred_airlines:
            # move these preferred ones to the top
            # why 'not in': because the key will return 0 for preferred flights and 1 for flights that
            # are not preferred. Since 0<1, preferred flights will go up in the ascending order.
            flight_options.sort(key=lambda x: x['airline'] not in preferred_airlines)

            # Add a flag about preference
            for flight in flight_options:
                if flight['airline'] in preferred_airlines:
                    flight['preferred'] = True
                else:
                    flight['preferred'] = False

    return json.dumps(flight_options)