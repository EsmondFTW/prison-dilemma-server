import asyncio
import websockets
import json

# Define the payoff matrix
payoff_matrix = {
    ('C', 'C'): (3, 3),  # Both cooperate
    ('D', 'D'): (1, 1),  # Both defect
    ('C', 'D'): (0, 5),  # Player 1 cooperates, Player 2 defects
    ('D', 'C'): (5, 0),  # Player 1 defects, Player 2 cooperates
}

clients = {}
moves = {} # Dictionary to store moves

async def compute_result():
    if len(moves) == 2:
        player1, player2 = moves.keys()
        move1, move2 = moves.values()
        result = payoff_matrix[(move1, move2)]
        print(result[0], result[1])
        # Send results to both clients

        await clients[player1].send(json.dumps({"result": result[0], "move": move2}))
        await clients[player2].send(json.dumps({"result": result[1], "move": move1}))
        
        # Reset for the next round
        moves.clear()

async def handle_client(websocket, path):
    try:
        # Register client
        player_id = await websocket.recv()
        clients[player_id] = websocket
        print(player_id)

        # Send number of rounds to Client
        await websocket.send("5")

        # Wait for moves
        while True:
            data = await websocket.recv()
            move_data = json.loads(data)
            moves[move_data['player_id']] = move_data['move']
            
            # Compute results if both players have sent their moves
            await compute_result()
    
    except websockets.ConnectionClosed:
        print(f"Connection closed for {player_id}")
        del clients[player_id]

async def main():
    async with websockets.serve(handle_client, "localhost", 6789):
        await asyncio.Future()  # run forever

asyncio.run(main())
