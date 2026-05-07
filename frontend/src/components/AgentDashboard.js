import React, { useState, useEffect } from 'react';
import { Paper, Typography, List, ListItem, ListItemText, CircularProgress, Chip } from '@mui/material';
import { getJSON } from '../api';

const AgentDashboard = () => {
  const [agents, setAgents] = useState({});
  const [loading, setLoading] = useState(true);

  const fetchStatus = async () => {
    try {
      const data = await getJSON('/agents/status');
      setAgents(data);
    } catch (e) {
      console.error("Failed to fetch agent status", e);
      setAgents({});
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Paper elevation={4} style={{ padding: '20px', backgroundColor: '#1e1e1e', color: '#fff', borderRadius: '12px' }}>
      <Typography variant="h5" gutterBottom style={{ fontWeight: 'bold', color: '#90caf9' }}>
        Service Runtime
      </Typography>
      
      {loading ? (
        <CircularProgress color="secondary" />
      ) : (
        <List>
          {Object.entries(agents).map(([name, info]) => (
            <ListItem key={name} style={{ borderBottom: '1px solid #333' }}>
              <ListItemText 
                primary={<Typography style={{fontWeight: 'bold'}}>{name}</Typography>} 
                secondary={
                   <Typography variant="caption" style={{color: '#aaa', wordBreak: 'break-all'}}>
                       {info.address}
                   </Typography>
                } 
              />
              <Chip 
                label={info.status} 
                color={info.status === 'Ready' ? 'success' : 'error'} 
                size="small" 
                style={{ fontWeight: 'bold' }}
              />
            </ListItem>
          ))}
          {Object.keys(agents).length === 0 && (
            <Typography style={{ color: '#ff6666' }}>Cannot connect to BioAgents API</Typography>
          )}
        </List>
      )}
    </Paper>
  );
};

export default AgentDashboard;
