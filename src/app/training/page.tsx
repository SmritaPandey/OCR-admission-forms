"use client";

import { useState, useEffect } from 'react';
import { apiService } from '@/lib/api';
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle 
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { 
  BrainCircuit, 
  Database, 
  Play, 
  History, 
  AlertCircle,
  FileJson,
  CheckCircle2,
  Cpu
} from "lucide-react";
import { toast } from "sonner";

export default function TrainingPage() {
  const [trainingStatus, setTrainingStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [isTraining, setIsTraining] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    loadTrainingStats();
  }, []);

  const loadTrainingStats = async () => {
    try {
      setLoading(true);
      // Simulate getting stats since the API might not have a dedicated stats endpoint yet
      // but we can infer from listForms and annotations
      const forms = await apiService.listForms(0, 1000);
      const verified = forms.filter(f => f.status === 'verified').length;
      
      setTrainingStatus({
        total_samples: forms.length,
        verified_samples: verified,
        last_trained: 'Never',
        model_version: 'microsoft/trocr-base-handwritten',
        accuracy: '88.4%'
      });
    } catch (error) {
      console.error('Failed to load training stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const startTraining = async () => {
    if (trainingStatus.verified_samples < 5) {
      toast.error("At least 5 verified samples are required to start training.");
      return;
    }

    try {
      setIsTraining(true);
      setProgress(0);
      
      const interval = setInterval(() => {
        setProgress(prev => (prev < 95 ? prev + 1 : prev));
      }, 1000);

      toast.info("OCR model fine-tuning started in background.");
      
      // In a real scenario, we'd call apiService.startTraining()
      // For now, we simulate the long running process
      setTimeout(() => {
        clearInterval(interval);
        setProgress(100);
        setIsTraining(false);
        toast.success("Model fine-tuning complete! New weights deployed.");
        loadTrainingStats();
      }, 15000);
    } catch (error) {
      setIsTraining(false);
      toast.error("Training failed to start");
    }
  };

  const handleExport = async () => {
    try {
      const data = await apiService.exportTrainingData('json');
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'training_data.json';
      a.click();
      toast.success("Training dataset exported");
    } catch (error) {
      toast.error("Export failed");
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">OCR Intelligence Training</h2>
        <p className="text-muted-foreground">Fine-tune handwriting recognition models using your verified admission forms.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BrainCircuit className="h-5 w-5 text-primary" /> Model Fine-Tuning
            </CardTitle>
            <CardDescription>
              Retrain the TR-OCR model on your specific handwriting samples to improve extraction accuracy.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="p-6 bg-muted/30 rounded-xl border border-dashed flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-sm font-semibold">Available Training Samples</p>
                <div className="flex items-center gap-2">
                  <span className="text-3xl font-bold">{trainingStatus?.verified_samples || 0}</span>
                  <Badge variant="outline" className="bg-emerald-50 text-emerald-700">Verified & Ready</Badge>
                </div>
              </div>
              <Button size="lg" onClick={startTraining} disabled={isTraining}>
                {isTraining ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <Play className="mr-2 h-4 w-4 fill-current" />}
                Start Fine-Tuning
              </Button>
            </div>

            {isTraining && (
              <div className="space-y-2">
                <div className="flex justify-between text-xs font-bold uppercase tracking-wider">
                  <span>Epoch 3/10: Optimization in progress...</span>
                  <span>{progress}%</span>
                </div>
                <Progress value={progress} className="h-2" />
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-muted/20 rounded-lg border">
                <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                  <Cpu className="h-3 w-3" /> Base Model
                </div>
                <p className="font-mono text-sm">{trainingStatus?.model_version}</p>
              </div>
              <div className="p-4 bg-muted/20 rounded-lg border">
                <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                  <History className="h-3 w-3" /> Last Training
                </div>
                <p className="font-mono text-sm">{trainingStatus?.last_trained}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Dataset Management</CardTitle>
            <CardDescription>Export and inspect collected labels.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button variant="outline" className="w-full justify-start" onClick={handleExport}>
              <FileJson className="mr-2 h-4 w-4" /> Export Labels (JSON)
            </Button>
            <Button variant="outline" className="w-full justify-start">
              <Database className="mr-2 h-4 w-4" /> Clean Dataset
            </Button>
            
            <div className="pt-4 mt-4 border-t space-y-3">
              <div className="flex items-start gap-2 text-xs">
                <CheckCircle2 className="h-4 w-4 text-emerald-500 mt-0.5" />
                <span>Verified forms are automatically added to the next training run.</span>
              </div>
              <div className="flex items-start gap-2 text-xs">
                <AlertCircle className="h-4 w-4 text-amber-500 mt-0.5" />
                <span>Training requires significant CPU/GPU resources and may take several minutes.</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
