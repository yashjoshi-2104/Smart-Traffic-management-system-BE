# backend/services/websocket_handler.py
"""
WebSocket handler for real-time state broadcasting
"""

import asyncio
import json
from typing import Set
from fastapi import WebSocket


class WebSocketManager:
    """
    Manages WebSocket connections and broadcasts
    """
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        print(f"✅ WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        self.active_connections.discard(websocket)
        print(f"❌ WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """
        Broadcast message to all connected clients
        
        Args:
            message (dict): Message to broadcast
        """
        if not self.active_connections:
            return
        
        # Convert to JSON
        message_json = json.dumps(message)
        
        # Send to all connections
        disconnected = set()
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                print(f"⚠️  Error sending to client: {e}")
                disconnected.add(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
    
    async def send_personal(self, message: dict, websocket: WebSocket):
        """
        Send message to specific client
        
        Args:
            message (dict): Message to send
            websocket (WebSocket): Target client
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"⚠️  Error sending personal message: {e}")
            self.disconnect(websocket)


# Global WebSocket manager
ws_manager = WebSocketManager()