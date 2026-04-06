"use client";

import React, { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  FlaskConical,
  Play,
  Pause,
  CheckCircle,
  XCircle,
  TrendingUp,
  TrendingDown,
  Users,
  BarChart3,
  AlertCircle,
  Trophy,
  Target,
} from "lucide-react";

interface ABTestResult {
  test_id: string;
  test_name: string;
  status: string;
  control_sample_size: number;
  treatment_sample_size: number;
  control_open_rate: number;
  control_engagement_score: number;
  treatment_open_rate: number;
  treatment_engagement_score: number;
  open_rate_p_value?: number;
  engagement_p_value?: number;
  winner_group?: string;
  is_significant: boolean;
  should_rollout: boolean;
  rollout_recommendation?: string;
}

interface PreferenceABTestResultsPanelProps {
  tests: ABTestResult[];
  loading?: boolean;
  onCreateTest?: (config: {
    test_name: string;
    hypothesis: string;
    recommendation_type: string;
    segment_type: string;
    duration_days: number;
  }) => Promise<void>;
  onStartTest?: (testId: string) => Promise<void>;
  onPauseTest?: (testId: string) => Promise<void>;
  onCompleteTest?: (testId: string) => Promise<void>;
  onRollout?: (testId: string) => Promise<void>;
}

export function PreferenceABTestResultsPanel({
  tests,
  loading = false,
  onCreateTest,
  onStartTest,
  onPauseTest,
  onCompleteTest,
  onRollout,
}: PreferenceABTestResultsPanelProps) {
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newTest, setNewTest] = useState({
    test_name: "",
    hypothesis: "",
    recommendation_type: "frequency_optimization",
    segment_type: "all_customers",
    duration_days: 14,
  });
  const [processing, setProcessing] = useState(false);

  const handleCreate = async () => {
    if (!onCreateTest) return;
    setProcessing(true);
    try {
      await onCreateTest(newTest);
      setShowCreateDialog(false);
      setNewTest({
        test_name: "",
        hypothesis: "",
        recommendation_type: "frequency_optimization",
        segment_type: "all_customers",
        duration_days: 14,
      });
    } finally {
      setProcessing(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "running":
        return { variant: "default" as const, icon: <Play className="h-3 w-3" />, label: "Running" };
      case "draft":
        return { variant: "secondary" as const, icon: <FlaskConical className="h-3 w-3" />, label: "Draft" };
      case "paused":
        return { variant: "outline" as const, icon: <Pause className="h-3 w-3" />, label: "Paused" };
      case "completed":
        return { variant: "default" as const, icon: <CheckCircle className="h-3 w-3" />, label: "Completed" };
      default:
        return { variant: "outline" as const, icon: null, label: status };
    }
  };

  const getWinnerBadge = (winner?: string) => {
    if (!winner) return null;
    switch (winner) {
      case "treatment":
        return { variant: "default" as const, icon: <Trophy className="h-3 w-3" />, label: "Treatment Won" };
      case "control":
        return { variant: "secondary" as const, icon: <Target className="h-3 w-3" />, label: "Control Won" };
      case "inconclusive":
        return { variant: "outline" as const, icon: <AlertCircle className="h-3 w-3" />, label: "Inconclusive" };
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FlaskConical className="h-5 w-5" />
            A/B Tests
          </CardTitle>
          <CardDescription>Loading...</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse">
              <div className="h-24 bg-muted rounded-lg" />
            </div>
          ))}
        </CardContent>
      </Card>
    );
  }

  const runningTests = tests.filter((t) => t.status === "running");
  const completedTests = tests.filter((t) => t.status === "completed");
  const draftTests = tests.filter((t) => t.status === "draft");

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <FlaskConical className="h-5 w-5" />
              Preference A/B Tests
            </CardTitle>
            <CardDescription>
              Validate preference recommendations with controlled experiments
            </CardDescription>
          </div>
          {onCreateTest && (
            <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
              <DialogTrigger asChild>
                <Button size="sm">
                  <FlaskConical className="h-4 w-4 mr-2" />
                  New Test
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Create A/B Test</DialogTitle>
                  <DialogDescription>
                    Set up a new experiment to validate preference recommendations
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="test_name">Test Name</Label>
                    <Input
                      id="test_name"
                      value={newTest.test_name}
                      onChange={(e) => setNewTest({ ...newTest, test_name: e.target.value })}
                      placeholder="Weekly Digest Optimization"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="hypothesis">Hypothesis</Label>
                    <Textarea
                      id="hypothesis"
                      value={newTest.hypothesis}
                      onChange={(e) => setNewTest({ ...newTest, hypothesis: e.target.value })}
                      placeholder="Switching to weekly email digests will improve engagement by 20%"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Recommendation Type</Label>
                      <Select
                        value={newTest.recommendation_type}
                        onValueChange={(v) => setNewTest({ ...newTest, recommendation_type: v })}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="frequency_optimization">Frequency</SelectItem>
                          <SelectItem value="channel_optimization">Channel</SelectItem>
                          <SelectItem value="fatigue_prevention">Fatigue Prevention</SelectItem>
                          <SelectItem value="batch_vs_realtime">Batch vs Real-time</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Segment</Label>
                      <Select
                        value={newTest.segment_type}
                        onValueChange={(v) => setNewTest({ ...newTest, segment_type: v })}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all_customers">All Customers</SelectItem>
                          <SelectItem value="all_owners">All Owners</SelectItem>
                          <SelectItem value="cohort">Specific Cohort</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>Duration (days)</Label>
                    <Input
                      type="number"
                      value={newTest.duration_days}
                      onChange={(e) => setNewTest({ ...newTest, duration_days: parseInt(e.target.value) || 14 })}
                      min={7}
                      max={90}
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleCreate} disabled={processing || !newTest.test_name || !newTest.hypothesis}>
                    Create Test
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Running Tests */}
        {runningTests.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-sm font-medium flex items-center gap-2">
              <Play className="h-4 w-4 text-green-500" />
              Running Tests ({runningTests.length})
            </h4>
            {runningTests.map((test) => (
              <div key={test.test_id} className="p-4 rounded-lg border bg-green-50/50 dark:bg-green-950/20">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <h5 className="font-medium">{test.test_name}</h5>
                    <p className="text-sm text-muted-foreground">
                      {test.control_sample_size + test.treatment_sample_size} users enrolled
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="default">
                      <Play className="h-3 w-3 mr-1" />
                      Running
                    </Badge>
                    {onPauseTest && (
                      <Button size="sm" variant="outline" onClick={() => onPauseTest(test.test_id)}>
                        <Pause className="h-4 w-4" />
                      </Button>
                    )}
                    {onCompleteTest && (
                      <Button size="sm" onClick={() => onCompleteTest(test.test_id)}>
                        Complete
                      </Button>
                    )}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div className="p-3 rounded bg-muted">
                    <div className="text-muted-foreground mb-1">Control</div>
                    <div className="text-lg font-bold">{(test.control_open_rate * 100).toFixed(1)}%</div>
                    <div className="text-xs text-muted-foreground">open rate</div>
                  </div>
                  <div className="p-3 rounded bg-muted">
                    <div className="text-muted-foreground mb-1">Treatment</div>
                    <div className="text-lg font-bold">{(test.treatment_open_rate * 100).toFixed(1)}%</div>
                    <div className="text-xs text-muted-foreground">open rate</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Completed Tests */}
        {completedTests.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-sm font-medium flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-blue-500" />
              Completed Tests ({completedTests.length})
            </h4>
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Test</TableHead>
                    <TableHead className="text-center">Sample</TableHead>
                    <TableHead className="text-right">Control</TableHead>
                    <TableHead className="text-right">Treatment</TableHead>
                    <TableHead className="text-center">Significant</TableHead>
                    <TableHead>Winner</TableHead>
                    <TableHead className="text-center">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {completedTests.map((test) => {
                    const winner = getWinnerBadge(test.winner_group);
                    const improvement = test.treatment_engagement_score - test.control_engagement_score;
                    return (
                      <TableRow key={test.test_id}>
                        <TableCell className="font-medium">{test.test_name}</TableCell>
                        <TableCell className="text-center">
                          <div className="flex items-center justify-center gap-1">
                            <Users className="h-3 w-3" />
                            {test.control_sample_size + test.treatment_sample_size}
                          </div>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="text-sm">
                            {(test.control_open_rate * 100).toFixed(1)}%
                          </div>
                          <div className="text-xs text-muted-foreground">
            Score: {test.control_engagement_score.toFixed(1)}
                          </div>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="text-sm flex items-center justify-end gap-1">
                            {(test.treatment_open_rate * 100).toFixed(1)}%
                            {improvement > 0 ? (
                              <TrendingUp className="h-3 w-3 text-green-500" />
                            ) : improvement < 0 ? (
                              <TrendingDown className="h-3 w-3 text-red-500" />
                            ) : null}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            Score: {test.treatment_engagement_score.toFixed(1)}
                          </div>
                        </TableCell>
                        <TableCell className="text-center">
                          {test.is_significant ? (
                            <Badge variant="default" className="bg-green-500">
                              <CheckCircle className="h-3 w-3 mr-1" />
                              Yes
                            </Badge>
                          ) : (
                            <Badge variant="outline">
                              <XCircle className="h-3 w-3 mr-1" />
                              No
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          {winner && (
                            <Badge variant={winner.variant}>
                              {winner.icon}
                              <span className="ml-1">{winner.label}</span>
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-center">
                          {test.should_rollout && onRollout && (
                            <Button size="sm" onClick={() => onRollout(test.test_id)}>
                              <BarChart3 className="h-4 w-4 mr-1" />
                              Rollout
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          </div>
        )}

        {/* Draft Tests */}
        {draftTests.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-sm font-medium flex items-center gap-2">
              <FlaskConical className="h-4 w-4 text-gray-500" />
              Draft Tests ({draftTests.length})
            </h4>
            {draftTests.map((test) => (
              <div key={test.test_id} className="p-4 rounded-lg border bg-muted/50">
                <div className="flex items-center justify-between">
                  <div>
                    <h5 className="font-medium">{test.test_name}</h5>
                    <p className="text-sm text-muted-foreground">Not yet started</p>
                  </div>
                  {onStartTest && (
                    <Button size="sm" onClick={() => onStartTest(test.test_id)}>
                      <Play className="h-4 w-4 mr-2" />
                      Start
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {tests.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            <FlaskConical className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p>No A/B tests yet</p>
            <p className="text-sm">Create your first test to validate recommendations</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default PreferenceABTestResultsPanel;
