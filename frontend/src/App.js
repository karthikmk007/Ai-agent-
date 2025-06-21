import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Color mapping for Among Us characters
const CHARACTER_COLORS = {
  red: 'bg-red-500',
  blue: 'bg-blue-500', 
  green: 'bg-green-500',
  yellow: 'bg-yellow-400',
  orange: 'bg-orange-500',
  purple: 'bg-purple-500',
  pink: 'bg-pink-500',
  cyan: 'bg-cyan-500'
};

const PRIORITY_COLORS = {
  emergency: 'bg-red-600 text-white',
  work: 'bg-blue-600 text-white', 
  health: 'bg-green-600 text-white'
};

const PRIORITY_LABELS = {
  emergency: '🚨 EMERGENCY',
  work: '💼 WORK',
  health: '🏥 HEALTH'
};

// Among Us Character Component
const AmongUsCharacter = ({ color, isOnToilet = false, isActive = false, size = 'normal' }) => {
  const sizeClasses = {
    small: 'w-8 h-12',
    normal: 'w-12 h-16', 
    large: 'w-16 h-20'
  };

  const opacity = isActive ? 'opacity-100' : 'opacity-70';
  
  return (
    <div className={`relative ${sizeClasses[size]} ${opacity} transition-all duration-300`}>
      {/* Character Body */}
      <div className={`${CHARACTER_COLORS[color]} rounded-full ${sizeClasses[size]} relative shadow-lg`}>
        {/* Visor */}
        <div className="absolute top-1 left-1/2 transform -translate-x-1/2 w-8 h-6 bg-blue-200 rounded-full opacity-80"></div>
        
        {/* Backpack */}
        <div className={`absolute -right-1 top-2 w-2 h-4 ${CHARACTER_COLORS[color]} rounded opacity-90`}></div>
        
        {/* Legs (only show if not on toilet) */}
        {!isOnToilet && (
          <div className="absolute -bottom-2 left-1/2 transform -translate-x-1/2 flex space-x-1">
            <div className={`w-2 h-3 ${CHARACTER_COLORS[color]} rounded-full`}></div>
            <div className={`w-2 h-3 ${CHARACTER_COLORS[color]} rounded-full`}></div>
          </div>
        )}
      </div>
      
      {/* Toilet (only show when on toilet) */}
      {isOnToilet && (
        <div className="absolute -bottom-4 left-1/2 transform -translate-x-1/2">
          <div className="w-10 h-6 bg-white rounded-lg border-2 border-gray-300"></div>
        </div>
      )}
      
      {/* Steam animation (only when on toilet) */}
      {isOnToilet && (
        <div className="absolute -top-2 left-1/2 transform -translate-x-1/2">
          <div className="animate-bounce">💨</div>
        </div>
      )}
    </div>
  );
};

// Emergency Alert Modal
const EmergencyAlert = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-red-600 bg-opacity-90 flex items-center justify-center z-50 animate-pulse">
      <div className="bg-white p-8 rounded-lg shadow-2xl text-center max-w-md mx-4">
        <div className="text-6xl mb-4">🚨</div>
        <h2 className="text-3xl font-bold text-red-600 mb-4">EMERGENCY!</h2>
        <p className="text-lg mb-6">Someone needs the bathroom urgently!</p>
        <button 
          onClick={onClose}
          className="bg-red-600 text-white px-6 py-3 rounded-lg font-bold hover:bg-red-700 transition-colors"
        >
          OK, GOT IT!
        </button>
      </div>
    </div>
  );
};

function App() {
  const [users, setUsers] = useState([]);
  const [queue, setQueue] = useState([]);
  const [currentUser, setCurrentUser] = useState(null);
  const [completedQueue, setCompletedQueue] = useState([]);
  const [utilities, setUtilities] = useState([]);
  const [hygieneRatings, setHygieneRatings] = useState([]);
  const [showEmergencyAlert, setShowEmergencyAlert] = useState(false);
  
  // Form states
  const [newUserName, setNewUserName] = useState('');
  const [newUserColor, setNewUserColor] = useState('red');
  const [selectedUserId, setSelectedUserId] = useState('');
  const [selectedPriority, setSelectedPriority] = useState('work');
  const [queueReason, setQueueReason] = useState('');
  const [newUtilityName, setNewUtilityName] = useState('');
  const [selectedBuyerId, setSelectedBuyerId] = useState('');
  const [hygieneRating, setHygieneRating] = useState(5);
  const [hygieneComment, setHygieneComment] = useState('');

  useEffect(() => {
    fetchData();
    // Refresh data every 10 seconds
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [usersRes, queueRes, currentRes, completedRes, utilitiesRes, hygieneRes] = await Promise.all([
        axios.get(`${API}/users`),
        axios.get(`${API}/queue`),
        axios.get(`${API}/queue/current`),
        axios.get(`${API}/queue/completed`),
        axios.get(`${API}/utilities`),
        axios.get(`${API}/hygiene-rating`)
      ]);
      
      setUsers(usersRes.data);
      setQueue(queueRes.data);
      setCurrentUser(currentRes.data);
      setCompletedQueue(completedRes.data);
      setUtilities(utilitiesRes.data);
      setHygieneRatings(hygieneRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
    }
  };

  const createUser = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/users`, {
        name: newUserName,
        color: newUserColor
      });
      setNewUserName('');
      fetchData();
    } catch (error) {
      alert(error.response?.data?.detail || 'Error creating user');
    }
  };

  const joinQueue = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/queue`, {
        user_id: selectedUserId,
        priority: selectedPriority,
        reason: queueReason
      });
      setQueueReason('');
      
      // Trigger emergency alert if priority is emergency
      if (selectedPriority === 'emergency') {
        triggerEmergencyAlert();
      }
      
      fetchData();
    } catch (error) {
      alert(error.response?.data?.detail || 'Error joining queue');
    }
  };

  const startUsingBathroom = async (queueItemId) => {
    try {
      await axios.post(`${API}/queue/${queueItemId}/start`);
      fetchData();
    } catch (error) {
      alert(error.response?.data?.detail || 'Error starting bathroom use');
    }
  };

  const completeBathroomUse = async (queueItemId) => {
    try {
      await axios.post(`${API}/queue/${queueItemId}/complete`);
      fetchData();
    } catch (error) {
      alert(error.response?.data?.detail || 'Error completing bathroom use');
    }
  };

  const triggerEmergencyAlert = async () => {
    try {
      await axios.post(`${API}/emergency-alert`);
      setShowEmergencyAlert(true);
    } catch (error) {
      console.error('Error triggering emergency alert:', error);
    }
  };

  const submitHygieneRating = async (e) => {
    e.preventDefault();
    if (!selectedUserId) {
      alert('Please select a user first');
      return;
    }
    
    try {
      await axios.post(`${API}/hygiene-rating`, {
        rated_by_user_id: selectedUserId,
        rating: hygieneRating,
        comment: hygieneComment
      });
      setHygieneComment('');
      fetchData();
    } catch (error) {
      alert(error.response?.data?.detail || 'Error submitting rating');
    }
  };

  const addUtility = async (e) => {
    e.preventDefault();
    if (!selectedBuyerId) {
      alert('Please select who bought this item');
      return;
    }
    
    try {
      await axios.post(`${API}/utilities`, {
        name: newUtilityName,
        last_bought_by_user_id: selectedBuyerId
      });
      setNewUtilityName('');
      fetchData();
    } catch (error) {
      alert(error.response?.data?.detail || 'Error adding utility');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-100 to-purple-100">
      {/* Emergency Alert Modal */}
      <EmergencyAlert 
        isOpen={showEmergencyAlert} 
        onClose={() => setShowEmergencyAlert(false)} 
      />
      
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold text-center mb-8 text-gray-800">
          🚽 Bathroom Queue Manager 
        </h1>

        {/* Current Bathroom Status */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
          <h2 className="text-2xl font-bold mb-4 text-center">Bathroom Status</h2>
          <div className="flex justify-center items-center space-x-8">
            {currentUser ? (
              <div className="text-center">
                <AmongUsCharacter 
                  color={currentUser.user_color} 
                  isOnToilet={true} 
                  isActive={true}
                  size="large"
                />
                <p className="mt-2 font-bold text-lg">{currentUser.user_name}</p>
                <p className="text-sm text-gray-600">Using bathroom</p>
                <span className={`inline-block px-3 py-1 rounded-full text-sm font-bold mt-2 ${PRIORITY_COLORS[currentUser.priority]}`}>
                  {PRIORITY_LABELS[currentUser.priority]}
                </span>
                <button 
                  onClick={() => completeBathroomUse(currentUser.id)}
                  className="mt-3 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors block mx-auto"
                >
                  ✅ Done
                </button>
              </div>
            ) : (
              <div className="text-center">
                <div className="w-20 h-24 bg-gray-200 rounded-lg flex items-center justify-center mb-4">
                  <span className="text-4xl">🚽</span>
                </div>
                <p className="text-lg font-bold text-green-600">Bathroom Available!</p>
              </div>
            )}
          </div>
        </div>

        {/* Queue Display */}
        <div className="grid md:grid-cols-2 gap-8 mb-8">
          {/* Waiting Queue */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-bold mb-4">🕒 Waiting Queue</h2>
            {queue.length === 0 ? (
              <p className="text-gray-500 text-center">No one in queue</p>
            ) : (
              <div className="space-y-3">
                {queue.map((item, index) => (
                  <div key={item.id} className="flex items-center justify-between bg-gray-50 p-3 rounded-lg">
                    <div className="flex items-center space-x-3">
                      <span className="font-bold text-lg">#{index + 1}</span>
                      <AmongUsCharacter color={item.user_color} size="small" />
                      <div>
                        <p className="font-bold">{item.user_name}</p>
                        <span className={`inline-block px-2 py-1 rounded-full text-xs font-bold ${PRIORITY_COLORS[item.priority]}`}>
                          {PRIORITY_LABELS[item.priority]}
                        </span>
                        {item.reason && <p className="text-sm text-gray-600 mt-1">{item.reason}</p>}
                      </div>
                    </div>
                    {index === 0 && !currentUser && (
                      <button 
                        onClick={() => startUsingBathroom(item.id)}
                        className="bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700 transition-colors text-sm"
                      >
                        Start Using
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Completed */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-bold mb-4">✅ Recently Completed</h2>
            {completedQueue.slice(0, 5).map((item) => (
              <div key={item.id} className="flex items-center space-x-3 mb-3 bg-green-50 p-2 rounded">
                <AmongUsCharacter color={item.user_color} size="small" />
                <div>
                  <p className="font-bold">{item.user_name}</p>
                  <p className="text-sm text-gray-600">
                    {new Date(item.completed_at).toLocaleTimeString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Controls */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          {/* Add User */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h3 className="text-lg font-bold mb-4">👥 Add Roommate</h3>
            <form onSubmit={createUser} className="space-y-4">
              <input
                type="text"
                placeholder="Name"
                value={newUserName}
                onChange={(e) => setNewUserName(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:border-blue-500"
                required
              />
              <select
                value={newUserColor}
                onChange={(e) => setNewUserColor(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:border-blue-500"
              >
                {Object.keys(CHARACTER_COLORS).map(color => (
                  <option key={color} value={color}>{color.toUpperCase()}</option>
                ))}
              </select>
              <button type="submit" className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition-colors">
                Add User
              </button>
            </form>
          </div>

          {/* Join Queue */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h3 className="text-lg font-bold mb-4">🏃‍♂️ Join Queue</h3>
            <form onSubmit={joinQueue} className="space-y-4">
              <select
                value={selectedUserId}
                onChange={(e) => setSelectedUserId(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:border-blue-500"
                required
              >
                <option value="">Select User</option>
                {users.map(user => (
                  <option key={user.id} value={user.id}>{user.name}</option>
                ))}
              </select>
              <select
                value={selectedPriority}
                onChange={(e) => setSelectedPriority(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:border-blue-500"
              >
                <option value="work">💼 Work</option>
                <option value="health">🏥 Health</option>
                <option value="emergency">🚨 Emergency</option>
              </select>
              <input
                type="text"
                placeholder="Reason (optional)"
                value={queueReason}
                onChange={(e) => setQueueReason(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:border-blue-500"
              />
              <button type="submit" className="w-full bg-green-600 text-white py-2 rounded-lg hover:bg-green-700 transition-colors">
                Join Queue
              </button>
            </form>
          </div>

          {/* Hygiene Rating */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h3 className="text-lg font-bold mb-4">⭐ Rate Hygiene</h3>
            <form onSubmit={submitHygieneRating} className="space-y-4">
              <select
                value={selectedUserId}
                onChange={(e) => setSelectedUserId(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:border-blue-500"
                required
              >
                <option value="">Who are you?</option>
                {users.map(user => (
                  <option key={user.id} value={user.id}>{user.name}</option>
                ))}
              </select>
              <div className="flex items-center space-x-2">
                <span>Rating:</span>
                {[1,2,3,4,5].map(star => (
                  <button
                    key={star}
                    type="button"
                    onClick={() => setHygieneRating(star)}
                    className={`text-2xl ${star <= hygieneRating ? 'text-yellow-500' : 'text-gray-300'}`}
                  >
                    ⭐
                  </button>
                ))}
              </div>
              <textarea
                placeholder="Comment (optional)"
                value={hygieneComment}
                onChange={(e) => setHygieneComment(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:border-blue-500"
                rows={2}
              />
              <button type="submit" className="w-full bg-yellow-600 text-white py-2 rounded-lg hover:bg-yellow-700 transition-colors">
                Submit Rating
              </button>
            </form>
          </div>
        </div>

        {/* Utilities Section */}
        <div className="grid md:grid-cols-2 gap-6">
          {/* Add Utility */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h3 className="text-lg font-bold mb-4">🧽 Add Bathroom Utility</h3>
            <form onSubmit={addUtility} className="space-y-4">
              <input
                type="text"
                placeholder="Utility name (e.g., Toilet Paper, Soap)"
                value={newUtilityName}
                onChange={(e) => setNewUtilityName(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:border-blue-500"
                required
              />
              <select
                value={selectedBuyerId}
                onChange={(e) => setSelectedBuyerId(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:border-blue-500"
                required
              >
                <option value="">Who bought this?</option>
                {users.map(user => (
                  <option key={user.id} value={user.id}>{user.name}</option>
                ))}
              </select>
              <button type="submit" className="w-full bg-purple-600 text-white py-2 rounded-lg hover:bg-purple-700 transition-colors">
                Add Utility
              </button>
            </form>
          </div>

          {/* Utilities List */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h3 className="text-lg font-bold mb-4">🧴 Bathroom Utilities</h3>
            <div className="space-y-3">
              {utilities.slice(0, 5).map(utility => (
                <div key={utility.id} className="bg-gray-50 p-3 rounded-lg">
                  <p className="font-bold">{utility.name}</p>
                  <p className="text-sm text-gray-600">
                    Last bought by: <span className="font-semibold">{utility.last_bought_by_name}</span>
                  </p>
                  <p className="text-sm text-gray-600">
                    Date: {new Date(utility.last_bought_date).toLocaleDateString()}
                  </p>
                  {utility.next_buyer_name && (
                    <p className="text-sm text-green-600">
                      Next buyer: <span className="font-semibold">{utility.next_buyer_name}</span>
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Users Display */}
        <div className="mt-8 bg-white rounded-lg shadow-lg p-6">
          <h3 className="text-lg font-bold mb-4">👥 Current Roommates</h3>
          <div className="flex flex-wrap gap-4">
            {users.map(user => (
              <div key={user.id} className="flex items-center space-x-2 bg-gray-50 p-3 rounded-lg">
                <AmongUsCharacter color={user.color} size="small" />
                <span className="font-bold">{user.name}</span>
                <span className={`w-4 h-4 rounded-full ${CHARACTER_COLORS[user.color]}`}></span>
              </div>
            ))}
          </div>
        </div>

        {/* Latest Hygiene Rating */}
        {hygieneRatings.length > 0 && (
          <div className="mt-8 bg-white rounded-lg shadow-lg p-6">
            <h3 className="text-lg font-bold mb-4">🧽 Latest Hygiene Rating</h3>
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="flex items-center space-x-2 mb-2">
                <span className="font-bold">{hygieneRatings[0].rated_by_name}</span>
                <span>rated:</span>
                <div className="flex">
                  {[1,2,3,4,5].map(star => (
                    <span key={star} className={star <= hygieneRatings[0].rating ? 'text-yellow-500' : 'text-gray-300'}>
                      ⭐
                    </span>
                  ))}
                </div>
              </div>
              {hygieneRatings[0].comment && (
                <p className="text-gray-600 italic">"{hygieneRatings[0].comment}"</p>
              )}
              <p className="text-sm text-gray-500 mt-2">
                {new Date(hygieneRatings[0].created_at).toLocaleString()}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;