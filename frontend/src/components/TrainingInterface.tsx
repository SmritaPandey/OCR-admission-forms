import { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import './TrainingInterface.css';

interface TrainingStats {
  total_forms: number;
  annotated_forms: number;
  unannotated_forms: number;
  annotation_percentage: number;
  total_fields: number;
}

interface TrainingConfig {
  model_type: 'trocr' | 'donut';
  base_model?: string;
  epochs: number;
  batch_size: number;
  learning_rate: number;
  output_model_dir?: string;
}

function TrainingInterface() {
  const [stats, setStats] = useState<TrainingStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [training, setTraining] = useState(false);
  const [trainingJob, setTrainingJob] = useState<any>(null);
  const [config, setConfig] = useState<TrainingConfig>({
    model_type: 'trocr',
    epochs: 20,
    batch_size: 8,
    learning_rate: 5e-5
  });

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      setLoading(true);
      // Use training API if available
      const response = await fetch('http://localhost:8000/api/training/stats');
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Failed to load training stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePrepareData = async () => {
    try {
      setLoading(true);
      const response = await fetch('http://localhost:8000/api/training/prepare-data?format=trocr&split=true', {
        method: 'POST'
      });
      const result = await response.json();
      alert(`Training data prepared! ${result.samples_extracted || 0} samples extracted.`);
      await loadStats();
    } catch (error: any) {
      alert(`Failed to prepare data: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleStartTraining = async () => {
    try {
      setTraining(true);
      const response = await fetch('http://localhost:8000/api/training/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      const result = await response.json();
      setTrainingJob(result);
      alert(`Training started! Job ID: ${result.job_id}\n\nNote: Training runs in background. Check console for progress.`);
    } catch (error: any) {
      alert(`Failed to start training: ${error.message}`);
    } finally {
      setTraining(false);
    }
  };

  return (
    <div className="training-interface">
      <h2>OCR Model Training</h2>
      <p className="description">
        Train CRAFT+TR-OCR and other OCR models on your verified forms
      </p>

      {loading && <div className="loading">Loading training stats...</div>}

      {stats && (
        <div className="training-stats">
          <h3>Training Data Statistics</h3>
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-value">{stats.total_forms}</div>
              <div className="stat-label">Total Forms</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.annotated_forms}</div>
              <div className="stat-label">Annotated Forms</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.annotation_percentage.toFixed(1)}%</div>
              <div className="stat-label">Annotation Coverage</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.total_fields}</div>
              <div className="stat-label">Total Fields</div>
            </div>
          </div>
        </div>
      )}

      <div className="training-actions">
        <div className="action-section">
          <h3>Step 1: Prepare Training Data</h3>
          <p>Extract training data from verified forms</p>
          <button 
            onClick={handlePrepareData}
            disabled={loading}
            className="btn btn-primary"
          >
            Prepare Training Data
          </button>
        </div>

        <div className="action-section">
          <h3>Step 2: Configure Training</h3>
          <div className="config-form">
            <div className="form-group">
              <label>Model Type:</label>
              <select 
                value={config.model_type}
                onChange={(e) => setConfig({...config, model_type: e.target.value as 'trocr' | 'donut'})}
              >
                <option value="trocr">TR-OCR (Handwritten Text Recognition)</option>
                <option value="donut">Donut (Document Understanding)</option>
              </select>
            </div>
            <div className="form-group">
              <label>Epochs:</label>
              <input
                type="number"
                min="1"
                max="100"
                value={config.epochs}
                onChange={(e) => setConfig({...config, epochs: parseInt(e.target.value) || 20})}
              />
            </div>
            <div className="form-group">
              <label>Batch Size:</label>
              <input
                type="number"
                min="1"
                max="32"
                value={config.batch_size}
                onChange={(e) => setConfig({...config, batch_size: parseInt(e.target.value) || 8})}
              />
            </div>
            <div className="form-group">
              <label>Learning Rate:</label>
              <input
                type="number"
                step="0.00001"
                value={config.learning_rate}
                onChange={(e) => setConfig({...config, learning_rate: parseFloat(e.target.value) || 5e-5})}
              />
            </div>
          </div>
        </div>

        <div className="action-section">
          <h3>Step 3: Start Training</h3>
          <p>Train CRAFT+TR-OCR model (best for handwritten forms)</p>
          <button
            onClick={handleStartTraining}
            disabled={training || loading}
            className="btn btn-primary btn-large"
          >
            {training ? 'Starting Training...' : 'Start Training CRAFT+TR-OCR'}
          </button>
        </div>

        {trainingJob && (
          <div className="training-job">
            <h4>Training Job Started</h4>
            <p>Job ID: {trainingJob.job_id}</p>
            <p>Status: {trainingJob.status}</p>
            <p className="note">
              Note: Training runs in the background. Check the terminal/console for progress.
              For full training, use: <code>./train_all_providers.sh</code>
            </p>
          </div>
        )}
      </div>

      <div className="training-info">
        <h3>Training Information</h3>
        <ul>
          <li><strong>CRAFT+TR-OCR</strong>: Best for handwritten student forms</li>
          <li><strong>Training Time</strong>: 1-6 hours depending on system</li>
          <li><strong>Recommended</strong>: 20+ epochs, batch size 8</li>
          <li><strong>After Training</strong>: Set TROCR_CUSTOM_MODEL_PATH in .env</li>
        </ul>
      </div>
    </div>
  );
}

export default TrainingInterface;
