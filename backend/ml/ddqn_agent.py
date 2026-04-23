"""
DDQN Agent for Traffic Signal Control

Double Deep Q-Network (DDQN) implementation with:
- Policy network (for action selection)
- Target network (for stable Q-value estimation)
- Experience replay
- Epsilon-greedy exploration
- DDQN update rule (reduces overestimation)
"""

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from typing import Tuple
import random


class DQN(nn.Module):
    """
    Deep Q-Network - Neural network that estimates Q-values
    """
    
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 128):
        """
        Initialize DQN network
        
        Args:
            state_dim: Dimension of state space (14 for our traffic env)
            action_dim: Number of actions (4 phases)
            hidden_dim: Size of hidden layers
        """
        super(DQN, self).__init__()
        
        # Three-layer fully connected network
        self.fc1 = nn.Linear(state_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, action_dim)
        
        # Initialize weights
        self._init_weights()
    
    def _init_weights(self):
        """Initialize network weights using Xavier initialization"""
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                nn.init.constant_(m.bias, 0)
    
    def forward(self, x):
        """
        Forward pass through network
        
        Args:
            x: Input state tensor
            
        Returns:
            Q-values for each action
        """
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x)  # No activation on output (Q-values can be any real number)


class DDQNAgent:
    """
    Double Deep Q-Network Agent
    """
    
    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        lr: float = 0.001,
        gamma: float = 0.99,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.01,
        epsilon_decay: float = 0.995,
        target_update_freq: int = 100,
        device: str = None
    ):
        """
        Initialize DDQN Agent
        
        Args:
            state_dim: Dimension of state space
            action_dim: Number of possible actions
            lr: Learning rate
            gamma: Discount factor for future rewards
            epsilon_start: Initial exploration rate
            epsilon_end: Minimum exploration rate
            epsilon_decay: Decay rate for epsilon
            target_update_freq: How often to update target network (in steps)
            device: 'cuda' or 'cpu' (auto-detect if None)
        """
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.target_update_freq = target_update_freq
        
        # Auto-detect device
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)
        
        print(f"🤖 DDQN Agent using device: {self.device}")
        
        # Create policy network (for selecting actions)
        self.policy_net = DQN(state_dim, action_dim).to(self.device)
        
        # Create target network (for stable Q-value estimation)
        self.target_net = DQN(state_dim, action_dim).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()  # Target network is always in eval mode
        
        # Optimizer
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=lr)
        
        # Loss function (Mean Squared Error)
        self.criterion = nn.MSELoss()
        
        # Training step counter
        self.steps = 0
        
    def select_action(self, state: np.ndarray, training: bool = True) -> int:
        """
        Select action using epsilon-greedy policy
        
        Args:
            state: Current state
            training: If True, use epsilon-greedy; if False, always exploit
            
        Returns:
            Selected action (0-3)
        """
        # Exploration: random action
        if training and random.random() < self.epsilon:
            return random.randint(0, self.action_dim - 1)
        
        # Exploitation: best action according to policy network
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            q_values = self.policy_net(state_tensor)
            return q_values.argmax().item()
    
    def train(self, batch: Tuple[np.ndarray, np.ndarray, np.ndarray, 
                                   np.ndarray, np.ndarray]) -> float:
        """
        Train the agent on a batch of experiences using DDQN algorithm
        
        DDQN Key Difference from DQN:
        - DQN: target = reward + gamma * max(target_net(next_state))
        - DDQN: best_action = argmax(policy_net(next_state))
                target = reward + gamma * target_net(next_state)[best_action]
        
        This reduces overestimation bias!
        
        Args:
            batch: Tuple of (states, actions, rewards, next_states, dones)
            
        Returns:
            Loss value
        """
        states, actions, rewards, next_states, dones = batch
        
        # Convert to tensors
        states = torch.FloatTensor(states).to(self.device)
        actions = torch.LongTensor(actions).to(self.device)
        rewards = torch.FloatTensor(rewards).to(self.device)
        next_states = torch.FloatTensor(next_states).to(self.device)
        dones = torch.FloatTensor(dones).to(self.device)
        
        # Current Q-values: Q(s, a)
        current_q_values = self.policy_net(states).gather(1, actions.unsqueeze(1)).squeeze()
        
        # DDQN Target Q-values
        with torch.no_grad():
            # Step 1: Use policy network to SELECT best action for next state
            next_actions = self.policy_net(next_states).argmax(1)
            
            # Step 2: Use target network to EVALUATE that action
            next_q_values = self.target_net(next_states).gather(1, next_actions.unsqueeze(1)).squeeze()
            
            # Target: r + gamma * Q_target(s', argmax_a Q_policy(s', a))
            target_q_values = rewards + (1 - dones) * self.gamma * next_q_values
        
        # Compute loss
        loss = self.criterion(current_q_values, target_q_values)
        
        # Optimize
        self.optimizer.zero_grad()
        loss.backward()
        
        # Gradient clipping (prevents exploding gradients)
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), max_norm=10.0)
        
        self.optimizer.step()
        
        # Update step counter
        self.steps += 1
        
        # Update target network periodically
        if self.steps % self.target_update_freq == 0:
            self.update_target_network()
        
        # Decay epsilon
        self.decay_epsilon()
        
        return loss.item()
    
    def update_target_network(self):
        """Copy weights from policy network to target network"""
        self.target_net.load_state_dict(self.policy_net.state_dict())
        print(f"🎯 Target network updated at step {self.steps}")
    
    def decay_epsilon(self):
        """Decay epsilon for exploration"""
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)
    
    def save(self, filepath: str):
        """
        Save agent state
        
        Args:
            filepath: Path to save checkpoint
        """
        checkpoint = {
            'policy_net_state_dict': self.policy_net.state_dict(),
            'target_net_state_dict': self.target_net.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'epsilon': self.epsilon,
            'steps': self.steps
        }
        torch.save(checkpoint, filepath)
        print(f"💾 Model saved to {filepath}")
    
    def load(self, filepath: str):
        """
        Load agent state
        
        Args:
            filepath: Path to checkpoint
        """
        checkpoint = torch.load(filepath, map_location=self.device)
        self.policy_net.load_state_dict(checkpoint['policy_net_state_dict'])
        self.target_net.load_state_dict(checkpoint['target_net_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.epsilon = checkpoint['epsilon']
        self.steps = checkpoint['steps']
        print(f"📂 Model loaded from {filepath}")
    
    def set_eval_mode(self):
        """Set agent to evaluation mode (no exploration)"""
        self.policy_net.eval()
        self.epsilon = 0.0
    
    def set_train_mode(self):
        """Set agent to training mode"""
        self.policy_net.train()