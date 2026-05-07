import React from 'react';
import { Paper, Typography, Grid, Chip, Alert } from '@mui/material';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Cell } from 'recharts';

const CHART_COLORS = ['#ff5252', '#4caf50', '#ffb74d', '#90caf9'];

const CompoundCard = ({ compound, resultType }) => {
  if (!compound) return null;

  const isPubChem = resultType === 'lookup';

  let name, props, similar, interactions, chartData = [];

  if (isPubChem) {
    // PubChem data — field name is iupac_name, not "name"
    name = compound.iupac_name
      || (Array.isArray(compound.synonyms) && compound.synonyms.length > 0
        ? compound.synonyms[0]
        : 'Unknown Compound');
    props = {
      "CID": compound.cid,
      "Formula": compound.molecular_formula,
      "Weight": compound.molecular_weight != null ? `${compound.molecular_weight} g/mol` : null,
      "Charge": compound.charge,
      "XLogP": compound.xlogp,
      "SMILES": compound.isomeric_smiles,
    };

    chartData = [
      { name: 'XLogP', val: compound.xlogp || 0 },
    ];
    similar = [];
    interactions = [];
  } else {
    // MeTTa / CompoundAgent data
    name = compound.molecule;
    const rp = compound.properties || {};

    props = {
      "Formula": rp.formula,
      "Weight": rp.molecular_weight != null ? `${rp.molecular_weight} g/mol` : null,
      "Category": Array.isArray(rp.categories) ? rp.categories.join(', ') : rp.categories,
      "Targets": Array.isArray(rp.targets) ? rp.targets.join(', ') : rp.targets,
      "Activity": rp.activity_score,
      "Selectivity": rp.selectivity,
      "Stability (h)": rp.stability_h,
    };

    chartData = [
      { name: 'Activity', val: parseFloat(rp.activity_score) || 0 },
      { name: 'Selectivity', val: parseFloat(rp.selectivity) || 0 },
    ];

    // Add stability as a normalised bar if present
    if (rp.stability_h != null) {
      chartData.push({ name: 'Stability', val: Math.min(parseFloat(rp.stability_h) / 1200, 1.0) });
    }

    similar = compound.similar_compounds || [];
    interactions = compound.known_interactions || [];
  }

  return (
    <Paper elevation={4} style={{ padding: '20px', backgroundColor: '#2a2a2a', color: '#fff', borderRadius: '12px', marginTop: '20px' }}>
      <Typography variant="h5" color="secondary" gutterBottom>{name}</Typography>
      {compound.mode && (
        <Alert severity={compound.mode === 'openai-primary' ? 'success' : 'info'} sx={{ mb: 2 }}>
          {compound.mode === 'openai-primary'
            ? `OpenAI primary analysis${compound.openai_model ? ` (${compound.openai_model})` : ''}`
            : `Local fallback${compound.fallback_reason ? `: ${compound.fallback_reason}` : ''}`}
        </Alert>
      )}

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Typography variant="h6" style={{ color: '#90caf9' }}>Properties</Typography>
          <ul style={{ listStyleType: 'none', paddingLeft: 0 }}>
            {Object.entries(props).map(([k, v]) => (
              v !== undefined && v !== null && v !== '' && (
                <li key={k} style={{ marginBottom: '8px', borderBottom: '1px solid #444', paddingBottom: '4px' }}>
                  <strong>{k}:</strong>{' '}
                  <span style={{ color: '#aaa' }}>{String(v)}</span>
                </li>
              )
            ))}
          </ul>

          {isPubChem && Array.isArray(compound.synonyms) && compound.synonyms.length > 0 && (
            <div style={{ marginTop: '10px' }}>
              <Typography variant="subtitle2" style={{ color: '#90caf9', marginBottom: '4px' }}>
                Also Known As
              </Typography>
              {compound.synonyms.map((s, i) => (
                <Chip
                  key={i}
                  label={s}
                  size="small"
                  style={{ margin: '2px', backgroundColor: '#444', color: '#fff' }}
                />
              ))}
            </div>
          )}
        </Grid>

        <Grid item xs={12} md={6}>
          <Typography variant="h6" style={{ color: '#90caf9' }}>Metrics</Typography>
          <div style={{ height: '200px', width: '100%' }}>
            <ResponsiveContainer>
              <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                <XAxis type="number" domain={[0, 1]} stroke="#aaa" />
                <YAxis dataKey="name" type="category" stroke="#aaa" width={80} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#333', border: 'none' }}
                  formatter={(value) => value.toFixed(3)}
                />
                <Bar dataKey="val" barSize={20}>
                  {chartData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Grid>

        {(similar.length > 0 || interactions.length > 0) && (
          <Grid item xs={12}>
            {similar.length > 0 && (
              <div style={{ marginBottom: '15px' }}>
                <Typography variant="subtitle2" style={{ color: '#90caf9' }}>Similar Compounds:</Typography>
                <div>
                  {similar.map((s, idx) => (
                    <Chip key={idx} label={s} style={{ margin: '4px', backgroundColor: '#444', color: '#fff' }} />
                  ))}
                </div>
              </div>
            )}

            {interactions.length > 0 && (
              <div>
                <Typography variant="subtitle2" style={{ color: '#ff5252' }}>Known Interactions:</Typography>
                <div>
                  {interactions.map((i, idx) => {
                    const effect = (i.effect || '').replace(/_/g, ' ');
                    const severity = (i.severity || 'unknown').toLowerCase();
                    const chipColor = severity === 'high' ? '#ff5252'
                      : severity === 'moderate' ? '#ffb74d'
                        : '#4caf50';
                    return (
                      <Chip
                        key={idx}
                        label={`${i.drug} — ${effect} (${severity})`}
                        style={{ margin: '4px', borderColor: chipColor, color: chipColor }}
                        variant="outlined"
                      />
                    );
                  })}
                </div>
              </div>
            )}
          </Grid>
        )}

        {compound.openai_analysis && (
          <Grid item xs={12}>
            <Paper style={{ padding: '15px', backgroundColor: '#333', marginTop: '10px', borderLeft: '4px solid #ce93d8' }}>
              <Typography variant="subtitle2" style={{ color: '#ce93d8', marginBottom: '5px' }}>OpenAI Analysis</Typography>
              <Typography variant="body2" sx={{ mb: 1 }}>{compound.openai_analysis.mechanistic_summary}</Typography>
              {compound.openai_analysis.strengths?.length > 0 && (
                <Typography variant="body2">Strengths: {compound.openai_analysis.strengths.join('; ')}</Typography>
              )}
              {compound.openai_analysis.risks?.length > 0 && (
                <Typography variant="body2">Risks: {compound.openai_analysis.risks.join('; ')}</Typography>
              )}
              {compound.openai_analysis.recommended_next_steps?.length > 0 && (
                <Typography variant="body2">Next: {compound.openai_analysis.recommended_next_steps.join('; ')}</Typography>
              )}
            </Paper>
          </Grid>
        )}
      </Grid>
    </Paper>
  );
};

export default CompoundCard;
