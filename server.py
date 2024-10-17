import asyncio
import websockets
import json
from collections import deque


# Define the payoff matrix
payoff_matrix = {
    ('C', 'C'): (3, 3),  # Both cooperate
    ('D', 'D'): (1, 1),  # Both defect
    ('C', 'D'): (0, 5),  # Player 1 cooperates, Player 2 defects
    ('D', 'C'): (5, 0),  # Player 1 defects, Player 2 cooperates
}


clients = {}
sessions = deque()  # Queue to manage sessions
visualizer = None


async def compute_result(session, round_number):
    player1, player2 = session.keys()
    move1, move2 = session.values()
    result = payoff_matrix[(move1, move2)]
    
    print(result[0], result[1])
    
    # Send results to both clients
    await clients[player1].send(json.dumps({"result": result[0], "move": move2}))
    await clients[player2].send(json.dumps({"result": result[1], "move": move1}))
    
   # Send data to visualizer
    if visualizer:
        data = {
            "Session_id": player1 + player2,
            "Team1": {"player_id": player1, "move": move1, "score": result[0], "round": round_number},
            "Team2": {"player_id": player2, "move": move2, "score": result[1], "round": round_number}
        }
        await visualizer.send(json.dumps(data))


async def handle_client(websocket, path):
    global visualizer
    try:
        # Register client
        player_id = await websocket.recv()

        if player_id in clients:
            await websocket.send("Connection rejected: Player ID already in use")
            await websocket.close()
            print(f"Connection rejected for player {player_id}: ID already in use")
            return

        if player_id == "Visualizer":
            print("Visualizer connected")
            visualizer = websocket
            # Keep visualizer connection active indefinitely
            while True:
                await asyncio.sleep(10)  # Prevent disconnection due to inactivity
        else:
            clients[player_id] = websocket
            print(f"Player {player_id} connected")

            # Check for an existing session with one player or an empty session
            if sessions and (len(sessions[0]) == 1 or (len(sessions[0]) == 0 and len(sessions) > 1)):
                session = sessions.popleft()  # Get the existing session
                session[player_id] = None  # Add the new player to the session
                if len(sessions) > 1 and len(session) == 0:
                    sessions.popleft()  # Remove the empty session if it's not the only one
                print(f"Player {player_id} joined an existing session")
            else:
                # Create new session id
                session = {player_id: None}  # Create a new session for the new player
                sessions.append(session)
                print(f"Player {player_id} started a new session")


            # Send number of rounds to Client
            await websocket.send("5")

            round_number = 1
            # Wait for moves
            while True:
                data = await websocket.recv()
                move_data = json.loads(data)
                session[player_id] = move_data['move']


                # Check if both players have made their moves and the session has 2 players
                if len(session) == 2 and None not in session.values():
                    await compute_result(session,round_number)
                    round_number+=1
                    sessions.append(session)  # Re-add the completed session for reuse


                    # Reset moves for the next round
                    for key in session.keys():
                        session[key] = None


    except websockets.ConnectionClosed:
        print(f"Connection closed for {player_id}")
        
        if player_id != "Visualizer":
            del clients[player_id]


        # Clean up the session if necessary
        for session in sessions:
            if player_id in session:
                del session[player_id]
                if len(session) == 0:  # If the session is now empty
                    sessions.remove(session)  # Remove the empty session
                elif len(session) < 2:  # If one player left, keep it for a new player
                    print(f"Session with {player_id} is waiting for another player.")
                break


async def main():
    async with websockets.serve(handle_client, "localhost", 6789):  
        await asyncio.Future()  # run forever


asyncio.run(main())