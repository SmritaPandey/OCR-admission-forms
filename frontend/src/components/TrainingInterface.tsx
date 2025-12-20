import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import './TrainingInterface.css';

interface TrainingStats {
  total_forms: number;
  annotated_forms: number;
  unannotated_forms: number;
  annotation_percentage: number;
  total_fields: number;
  total_checkboxes: number;
  field_types: Record<string, number>;
  checkbox_labels: Record<string, number>;
  forms_with_all_fields: number;
  forms_with_checkboxes: number;
}

interface ImprovementStats {
  corrections_since_training: number;
  last_training: string | null;
  total_models: number;
  pending_corrections: number;
  should_retrain: boolean;
}

interface TrainingConfig {
  epochs: number;
  batch_size: number;
  learning_rate: number;
  base_model?: string;
}

const TrainingInterface: React.FC = () => {
  const [stats, setStats] = useState<TrainingStats | null>(null);
  const [improvementStats, setImprovementStats] = useState<ImprovementStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [preparing, setPreparing] = useState(false);
  const [training, setTraining] = useState(false);
  const [trainingConfig, setTrainingConfig] = useState<TrainingConfig>({
    epochs: 10,
    batch_size: 8,
    learning_rate: 5e-5
  });
  const [preparationResult, setPreparationResult] = useState<any>(null);
  const [trainingResult, setTrainingResult] = useState<any>(null);

  useEffect(() => {
    loadStats();
    loadImprovementStats();
  }, []);

  const loadStats = async () => {
    try {
      const data = await apiService.getTrainingStats();
      setStats(data);
    } catch (error) {
      console.error('Failed to load training stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadImprovementStats = async () => {
    try {
      const data = await apiService.getImprovementStats();
      setImprovementStats(data);
    } catch (error) {
      console.error('Failed to load improvement stats:', error);
    }
  };

  const handlePrepareData = async (format: 'trocr' | 'donut' | 'both' = 'both') => {
    setPreparing(true);
    try {
      const result = await apiService.prepareTrainingData(format, true);
      setPreparationResult(result);
      alert(`Training data prepared successfully!\nSamples: ${result.samples_extracted}`);
    } catch (error: any) {
      alert(`Failed to prepare data: ${error.message || 'Unknown error'}`);
    } finally {
      setPreparing(false);
    }
  };

  const handleStartTraining = async () => {
    setTraining(true);
    try {
      const result = await apiService.startTraining({
        model_type: 'trocr',
        ...trainingConfig
      });
      setTrainingResult(result);
      alert(`Training job created!\nJob ID: ${result.job_id}\n\nNote: Training runs in background. Check terminal for progress.`);
    } catch (error: any) {
      alert(`Failed to start training: ${error.message || 'Unknown error'}`);
    } finally {
      setTraining(false);
    }
  };

  const handleTriggerRetraining = async () => {
    if (!confirm('Trigger retraining with accumulated corrections? This will use corrections made since last training.')) {
      return;
    }

    setTraining(true);
    try {
      const result = await apiService.triggerRetraining(trainingConfig);
      setTrainingResult(result);
      
      if (result.status === 'success') {
        alert(`Model retrained successfully!\nVersion: ${result.version}\nCorrections used: ${result.corrections_used}`);
        loadImprovementStats();
      } else {
        alert(`Retraining ${result.status}: ${result.reason || result.error}`);
      }
    } catch (error: any) {
      alert(`Failed to trigger retraining: ${error.message || 'Unknown error'}`);
    } finally {
      setTraining(false);
    }
  };

  if (loading) {
    return <div className="training-interface">Loading...</div>;
  }

  return (
    <div className="training-interface">
      <h1>Model Training & Continuous Improvement</h1>

      <div className="training-sections">
        {/* Training Statistics */}
        <section className="training-section">
          <h2>Training Data Statistics</h2>
          {stats && (
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
                <div className="stat-value">{stats.unannotated_forms}</div>
                <div className="stat-label">Unannotated Forms</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{stats.annotation_percentage.toFixed(1)}%</div>
                <div className="stat-label">Annotation Coverage</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{stats.total_fields}</div>
                <div className="stat-label">Total Fields</div>
              </div>
              <div className="stat-card">
                <div className="stat-value">{stats.forms_with_all_fields}</div>
                <div className="stat-label">Complete Forms</div>
              </div>
            </div>
          )}
        </section>

        {/* Continuous Improvement */}
        <section className="training-section">
          <h2>Continuous Improvement</h2>
          {improvementStats && (
            <div className="improvement-stats">
              <div className="stat-row">
                <span className="stat-label">Corrections Since Last Training:</span>
                <span className="stat-value">{improvementStats.corrections_since_training}</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Pending Corrections:</span>
                <span className="stat-value">{improvementStats.pending_corrections}</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Total Model Versions:</span>
                <span className="stat-value">{improvementStats.total_models}</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Last Training:</span>
                <span className="stat-value">
                  {improvementStats.last_training 
                    ? new Date(improvementStats.last_training).toLocaleString()
                    : 'Never'}
                </span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Ready for Retraining:</span>
                <span className={`stat-value ${improvementStats.should_retrain ? 'ready' : 'not-ready'}`}>
                  {improvementStats.should_retrain ? 'Yes' : 'No'}
                </span>
              </div>
              
              {improvementStats.should_retrain && (
                <button 
                  className="btn-primary"
                  onClick={handleTriggerRetraining}
                  disabled={training}
                >
                  {training ? 'Retraining...' : 'Trigger Retraining'}
                </button>
              )}
            </div>
          )}
        </section>

        {/* Data Preparation */}
        <section className="training-section">
          <h2>Prepare Training Data</h2>
          <p>Extract images and prepare datasets from annotated forms.</p>
          
          <div className="button-group">
            <button
              className="btn-secondary"
              onClick={() => handlePrepareData('trocr')}
              disabled={preparing}
            >
              {preparing ? 'Preparing...' : 'Prepare TrOCR Dataset'}
            </button>
            <button
              className="btn-secondary"
              onClick={() => handlePrepareData('donut')}
              disabled={preparing}
            >
              {preparing ? 'Preparing...' : 'Prepare Donut Dataset'}
            </button>
            <button
              className="btn-secondary"
              onClick={() => handlePrepareData('both')}
              disabled={preparing}
            >
              {preparing ? 'Preparing...' : 'Prepare Both'}
            </button>
          </div>

          {preparationResult && (
            <div className="result-box">
              <h3>Preparation Result</h3>
              <pre>{JSON.stringify(preparationResult, null, 2)}</pre>
            </div>
          )}
        </section>

        {/* Model Training */}
        <section className="training-section">
          <h2>Train Model</h2>
          <p>Train CRAFT+TrOCR model on prepared training data.</p>

          <div className="config-form">
            <div className="form-group">
              <label>Epochs:</label>
              <input
                type="number"
                value={trainingConfig.epochs}
                onChange={(e) => setTrainingConfig({...trainingConfig, epochs: parseInt(e.target.value)})}
                min={1}
                max={100}
              />
            </div>
            <div className="form-group">
              <label>Batch Size:</label>
              <input
                type="number"
                value={trainingConfig.batch_size}
                onChange={(e) => setTrainingConfig({...trainingConfig, batch_size: parseInt(e.target.value)})}
                min={1}
                max={32}
              />
            </div>
            <div className="form-group">
              <label>Learning Rate:</label>
              <input
                type="number"
                value={trainingConfig.learning_rate}
                onChange={(e) => setTrainingConfig({...trainingConfig, learning_rate: parseFloat(e.target.value)})}
                step="1e-6"
                min="1e-6"
                max="1e-2"
              />
            </div>
          </div>

          <button
            className="btn-primary"
            onClick={handleStartTraining}
            disabled={training || !stats || stats.annotated_forms === 0}
          >
            {training ? 'Starting...' : 'Start Training'}
          </button>

          {trainingResult && (
            <div className="result-box">
              <h3>Training Result</h3>
              <pre>{JSON.stringify(trainingResult, null, 2)}</pre>
            </div>
          )}
        </section>
      </div>
    </div>
  );
};

export default TrainingInterface;
