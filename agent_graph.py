from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END
from langgraph.config import get_stream_writer
from typing import Annotated, Dict, List, Any
from typing_extensions import TypedDict
from langgraph.types import interrupt

from pydantic import ValidationError
from dataclasses import dataclass

import logfire
import asyncio
import sys
import os

# import message classes from pydantic ai
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter
)

# import all our agents
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.info_gathering_agent import info_gathering_agent, TravelDetails
from agents.flight_agent import flight_agent, FlightDeps
from agents.hotel_agent import hotel_agent, HotelDeps
from agents.activity_agent import activity_agent
from agents.final_planner_agent import final_planner_agent
from agents.info_gathering_agent import info_gathering_agent

logfire.configure(send_to_logfire='if-token-present')

# 1. State: Define the state of our graph
class TravelState(TypedDict):
    # Chat messages and travel details. Chat messasges would be only required by our info_gathering_agent
    user_input: str
    messages: Annotated[List[bytes], lambda x,y : x+y]
    travel_details: Dict[str, any]

    # User preferences
    preferred_airlines: List[str]
    hotel_amenities: List[str]
    budget_level: str

    # Results from each agent
    flight_results: str
    hotel_results: str
    activity_results: str

    # Final summary
    final_plan: str

# Node functions for our graph
# info gathering node
async def gather_info(state: TravelState, writer) ->Dict[str, Any]:
    """Gather necessary travel information from the user"""
    user_input = state[user_input]

    # Convert message history into Pydanitc AI format
    message_history: List[ModelMessage] = []
    for message_row in state['messages']:
        message_history.extend(ModelMessagesTypeAdapter.validate_json(message_row))

    # Call the info gathering agent
    async with info_gathering_agent.run_stream(user_input, message_history=message_history) as result:
        curr_response = ""
        async for messasge, last in result.stream_structured(debounce_by=0.01):
            try:
                if last and not travel_details.response:
                    raise Exception("Incorrect travel details returned by agent.")
                travel_details = await result.validate_structured_result(
                    messasge,
                    allow_partial=not last
                )
            except ValidationError as e:
                continue

            if travel_details.response:
                writer(travel_details.response[len(curr_response):])
                curr_response = travel_details.response

    # return response and ask for more details if required
    data = await result.get_data()
    return {
        "travel_details": data.model_dump(),
        "messages": [result.new_messages_json()]
    }

# flight recommendation node
async def get_flight_recommendations(state:TravelState, writer) -> Dict[str, Any]:
    """Get flight recommendations based on travel details"""
    writer("\n###### Getting flight recommendations... ######")
    travel_details = state["travel_details"]
    preferred_airlines = state["preferred_airlines"]

    # Create the flight dependencies to pass on to the agent
    flight_dependencies = FlightDeps(preferred_airlines=preferred_airlines)

    # prepare the prompt
    prompt = f"I need flight recommendations from {travel_details['origin']} to {travel_details['destination']} on {travel_details['date_leaving']}. Return flight on {travel_details['date_returning']}."

    # call the flight agent
    result = await flight_agent.run(prompt=prompt, deps=flight_dependencies)

    # return the flight recommendations
    return {"flight_results": result.data}

# Hotel recommendation node
async def get_hotel_recommendations(state: TravelState, writer) -> Dict[str, Any]:
    """Get hotel recommendations based on travel details."""
    writer("\n#### Getting hotel recommendations...\n")
    travel_details = state["travel_details"]
    hotel_amenities = state['hotel_amenities']
    budget_level = state['budget_level']
    
    # Create hotel dependencies (in a real app, this would come from user preferences)
    hotel_dependencies = HotelDeps(
        hotel_amenities=hotel_amenities,
        budget_level=budget_level
    )
    
    # Prepare the prompt for the hotel agent
    prompt = f"I need hotel recommendations in {travel_details['destination']} from {travel_details['date_leaving']} to {travel_details['date_returning']} with a maximum price of ${travel_details['max_hotel_price']} per night."
    
    # Call the hotel agent
    result = await hotel_agent.run(prompt, deps=hotel_dependencies)
    
    # Return the hotel recommendations
    return {"hotel_results": result.data}

# Activity recommendation node
async def get_activity_recommendations(state: TravelState, writer) -> Dict[str, Any]:
    """Get activity recommendations based on travel details."""
    writer("\n#### Getting activity recommendations...\n")
    travel_details = state["travel_details"]
    
    # Prepare the prompt for the activity agent
    prompt = f"I need activity recommendations for {travel_details['destination']} from {travel_details['date_leaving']} to {travel_details['date_returning']}."
    
    # Call the activity agent
    result = await activity_agent.run(prompt)
    
    # Return the activity recommendations
    return {"activity_results": result.data}


# Final synthesizer
# Planning node
async def create_final_plan(state:TravelState, writer) -> Dict[str, Any]:
    """Create a final travel plan based on all recommendations"""
    travel_details = state["travel_details"]
    flight_results = state["flight_results"]
    hotel_results = state["hotel_results"]
    activity_results = state["activity_results"]
    
    prompt = f"""
    I am planning a trip to {travel_details['destination']} from {travel_details['origin']} on {travel_details['date_leaving']} and returning on {travel_details['date_returning']}.

    Here are the flight recommendations:
    {flight_results}

    Here are the hotel recommendations:
    {hotel_results}
    
    Here are the activity recommendations:
    {activity_results}
    
    Please create a comprehensive travel plan based on these recommendations.
    """

    # Call the final planner agent
    async with final_planner_agent.run_stream(prompt) as result:
        # Stream the partial text
        async for chunk in result.stream_text(delta=True):
            writer(chunk)

    # Return the final plan
    data = await result.get_data()
    return {"final_plan": data}

# Conditional edge: used while info gathering
def route_after_info_gathering(state: TravelState):
    """Determine what to do after gathering information"""
    travel_details = state["travel_details"]

    if not travel_details.get("all_details_given", False):
        return "get_next_user_message"
    
    # If all details are given, we can proceed to parallel recommendations
    # Return a list of Send objects to fan out to multiple nodes
    return ["get_flight_recommendations", "get_hotel_recommendations", "get_activity_recommendations"]

# To get a user message in between graph execution we need an Interrupt
def get_next_user_message(state: TravelState):
    value = interrupt({})

    # set the user's last message for the LLM to continue the conversation
    return {
        "user_input": value
    }

def build_travel_agent_graph():
    """Build and return the travel agent graph"""
    # Create the graph with our state
    graph = StateGraph(TravelState)

    # add nodes
    graph.add_node("gather_info", gather_info)
    graph.add_node("get_next_user_message", get_next_user_message)
    graph.add_node("get_flight_recommendations", get_flight_recommendations)
    graph.add_node("get_hotel_recommendations", get_hotel_recommendations)
    graph.add_node("get_activity_recommendations", get_activity_recommendations)
    graph.add_node("create_final_plan", create_final_plan)

    # Add edges
    graph.add_edge(START, "gather_info")

    # Conditional edge to get all info if not provided
    graph.add_conditional_edges(
        source="gather_info",
        path=route_after_info_gathering,
        then=["get_next_user_message", "get_flight_recommendations", "get_hotel_recommendations", "get_activity_recommendations"]
    )

    # If we have taken the counditional route to get next message, go back to gather info
    graph.add_edge("get_next_user_message", "gather_info")

    # Connect all recommendation nodes to the final planning node
    graph.add_edge("get_flight_recommendations", "create_final_plan")
    graph.add_edge("get_hotel_recommendations", "create_final_plan")
    graph.add_edge("get_activity_recommendations", "create_final_plan")

    graph.add_edge("create_final_plan", END)

    # Compile the graph
    memory = MemorySaver()
    return graph.compile(checkpointer=memory)

travel_agent_graph = build_travel_agent_graph()

# Function to run the agent
async def run_travel_agent(user_input: str):
    """Run the travel agent with the given input"""
    # Initialize the state
    initial_state = {
        "user_input": user_input,
        "travel_details": {},
        "flight_results": [],
        "hotel_results": [],
        "activity_results": [],
        "final_plan": ""
    }

    result = travel_agent_graph.ainvoke(initial_state)

    # return the final state
    return result["final_plan"]

async def main():
    # Example user input:
    user_input = "I want to plan a trip from New York to Paris from 06-15 to 06-22. My max budget for a hotel is $200 per night."

    # Run the travel agent
    final_plan = await run_travel_agent(user_input)

    # Print the final plan
    print("Final Travel Plan:")
    print(final_plan)


if __name__ ==  "__main__":
    asyncio.run(main())
