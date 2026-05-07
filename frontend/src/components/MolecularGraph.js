import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { Paper, Typography } from '@mui/material';
import { getJSON } from '../api';

const MolecularGraph = ({ highlightedMolecule }) => {
  const [data, setData] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const graphRef = useRef();

  useEffect(() => {
    const fetchGraphData = async () => {
      try {
        const json = await getJSON('/molecules');
        setData(json);
      } catch (e) {
        console.error('Failed to fetch graph data', e);
      } finally {
        setLoading(false);
      }
    };
    fetchGraphData();
  }, []);

  // When highlighted molecule changes, zoom to it
  useEffect(() => {
    if (!highlightedMolecule || !graphRef.current) return;
    const node = data.nodes.find((n) => n.id === highlightedMolecule);
    if (node && node.x != null && node.y != null) {
      graphRef.current.centerAt(node.x, node.y, 800);
      graphRef.current.zoom(4, 800);
    }
  }, [highlightedMolecule, data]);

  // Compute highlight sets in useMemo so callbacks get stable references
  const { highlightNodes, highlightLinks } = useMemo(() => {
    const hNodes = new Set();
    const hLinks = new Set();
    if (highlightedMolecule) {
      hNodes.add(highlightedMolecule);
      data.links.forEach((link) => {
        const srcId = typeof link.source === 'object' ? link.source.id : link.source;
        const tgtId = typeof link.target === 'object' ? link.target.id : link.target;
        if (srcId === highlightedMolecule || tgtId === highlightedMolecule) {
          hLinks.add(link);
          hNodes.add(srcId);
          hNodes.add(tgtId);
        }
      });
    }
    return { highlightNodes: hNodes, highlightLinks: hLinks };
  }, [highlightedMolecule, data]);

  const nodeColor = useCallback(
    (node) => {
      if (!highlightedMolecule) return null;
      if (node.id === highlightedMolecule) return '#ffeb3b';
      if (highlightNodes.has(node.id)) return '#ce93d8';
      return '#333';
    },
    [highlightedMolecule, highlightNodes]
  );

  const linkColor = useCallback(
    (link) => {
      if (highlightLinks.has(link)) return '#ffeb3b';
      if (link.type === 'interaction') {
        const sev = (link.severity || '').toLowerCase();
        if (sev === 'high') return '#ff5252';
        if (sev === 'moderate') return '#ffb74d';
        return '#ff8a80';
      }
      return highlightedMolecule ? '#2a2a2a' : '#aaaaaa';
    },
    [highlightedMolecule, highlightLinks]
  );

  const linkWidth = useCallback(
    (link) =>
      highlightLinks.has(link) ? 2.5 : link.type === 'interaction' ? Math.max(1.5, link.value) : 1,
    [highlightLinks]
  );

  return (
    <Paper
      elevation={4}
      style={{
        padding: '20px',
        backgroundColor: '#1e1e1e',
        color: '#fff',
        borderRadius: '12px',
        height: '500px',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <Typography variant="h5" gutterBottom style={{ fontWeight: 'bold', color: '#90caf9' }}>
        Knowledge Graph
        {highlightedMolecule && (
          <span style={{ fontSize: '0.75rem', color: '#ce93d8', marginLeft: '12px', fontWeight: 'normal' }}>
            — {highlightedMolecule} highlighted
          </span>
        )}
      </Typography>

      {loading ? (
        <Typography>Loading Knowledge Base...</Typography>
      ) : data.nodes.length === 0 ? (
        <Typography color="error">No data — is the server running on port 5000?</Typography>
      ) : (
        <div style={{ flex: 1, position: 'relative' }}>
          <ForceGraph2D
            ref={graphRef}
            graphData={data}
            nodeAutoColorBy={highlightedMolecule ? undefined : 'group'}
            nodeColor={highlightedMolecule ? nodeColor : undefined}
            nodeRelSize={1}
            nodeVal="val"
            nodeLabel={(node) => `${node.id} (${node.category})`}
            linkColor={linkColor}
            linkWidth={linkWidth}
            linkDirectionalParticles={(link) =>
              highlightLinks.has(link) || link.type === 'interaction' ? 2 : 0
            }
            linkDirectionalParticleSpeed={(link) => link.value * 0.01}
            backgroundColor="#1e1e1e"
            warmupTicks={100}
            cooldownTicks={0}
          />
        </div>
      )}
    </Paper>
  );
};

export default MolecularGraph;
