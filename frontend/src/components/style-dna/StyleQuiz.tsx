/**
 * Style Quiz Component
 * Interactive quiz to determine user's style preferences
 */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ChevronLeft, ChevronRight, Check } from 'lucide-react';
import { transitionFast } from '@/motion';

import { styleDNAApi, StyleQuizQuestion } from '@/lib/api/style-dna';

interface StyleQuizProps {
  onComplete: () => void;
  onCancel: () => void;
}

export const StyleQuiz: React.FC<StyleQuizProps> = ({ onComplete, onCancel }) => {
  const [questions, setQuestions] = useState<StyleQuizQuestion[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string[]>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadQuestions();
  }, []);

  const loadQuestions = async () => {
    try {
      setLoading(true);
      const data = await styleDNAApi.getQuizQuestions();
      setQuestions(data.questions);
    } catch (error) {
      console.error('Failed to load quiz questions:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = (questionId: string, optionId: string, isMulti: boolean) => {
    setAnswers((prev) => {
      const current = prev[questionId] || [];
      if (isMulti) {
        if (current.includes(optionId)) {
          return { ...prev, [questionId]: current.filter((id) => id !== optionId) };
        }
        return { ...prev, [questionId]: [...current, optionId] };
      }
      return { ...prev, [questionId]: [optionId] };
    });
  };

  const handleNext = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex(currentIndex + 1);
    }
  };

  const handlePrevious = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
    }
  };

  const handleSubmit = async () => {
    try {
      setSubmitting(true);
      await styleDNAApi.submitQuiz({
        quiz_type: 'initial',
        answers: questions.map((q) => ({
          question_id: q.id,
          selected_options: answers[q.id] || [],
          image_selections: [],
        })),
      });
      onComplete();
    } catch (error) {
      console.error('Failed to submit quiz:', error);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  const currentQuestion = questions[currentIndex];
  const progress = ((currentIndex + 1) / questions.length) * 100;
  const currentAnswer = answers[currentQuestion?.id] || [];
  const isMultiSelect = currentQuestion?.type === 'multi_select';

  return (
    <div className="max-w-2xl mx-auto">
      {/* Progress */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-muted-foreground">
            Question {currentIndex + 1} of {questions.length}
          </span>
          <span className="text-sm font-medium">{progress.toFixed(0)}%</span>
        </div>
        <Progress value={progress} className="h-2" />
      </div>

      {/* Question */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentQuestion?.id}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={transitionFast}
        >
          <Card>
            <CardHeader>
              <CardTitle>{currentQuestion?.question}</CardTitle>
              {isMultiSelect && (
                <p className="text-sm text-muted-foreground">
                  Select all that apply
                </p>
              )}
            </CardHeader>
            <CardContent>
              {/* Options */}
              <div
                className={cn(
                  'grid gap-3',
                  currentQuestion?.type === 'image_select'
                    ? 'grid-cols-2'
                    : 'grid-cols-1 sm:grid-cols-2'
                )}
              >
                {currentQuestion?.options.map((option) => {
                  const isSelected = currentAnswer.includes(option.id);

                  return (
                    <button
                      key={option.id}
                      onClick={() =>
                        handleSelect(
                          currentQuestion.id,
                          option.id,
                          isMultiSelect
                        )
                      }
                      className={cn(
                        'relative flex items-center gap-3 p-4 rounded-lg border transition-all',
                        'hover:border-primary/50 hover:bg-primary/5',
                        isSelected
                          ? 'border-primary bg-primary/10'
                          : 'border-border'
                      )}
                    >
                      {/* Color swatch */}
                      {option.color && (
                        <svg
                          viewBox="0 0 16 16"
                          className="w-8 h-8 flex-shrink-0"
                          aria-hidden="true"
                        >
                          <circle cx="8" cy="8" r="7" fill={option.color} stroke="currentColor" />
                        </svg>
                      )}

                      {/* Image */}
                      {option.image && (
                        <div className="w-16 h-16 rounded bg-muted flex-shrink-0 overflow-hidden">
                          <img
                            src={option.image}
                            alt={option.label}
                            className="w-full h-full object-cover"
                          />
                        </div>
                      )}

                      {/* Label */}
                      <span className="font-medium">{option.label}</span>

                      {/* Selected indicator */}
                      {isSelected && (
                        <div className="absolute top-2 right-2">
                          <Check className="h-5 w-5 text-primary" />
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </AnimatePresence>

      {/* Navigation */}
      <div className="flex items-center justify-between mt-6">
        <Button
          variant="outline"
          onClick={onCancel}
          disabled={submitting}
        >
          Cancel
        </Button>

        <div className="flex gap-2">
          {currentIndex > 0 && (
            <Button
              variant="outline"
              onClick={handlePrevious}
              disabled={submitting}
            >
              <ChevronLeft className="h-4 w-4 mr-1" />
              Back
            </Button>
          )}

          {currentIndex < questions.length - 1 ? (
            <Button onClick={handleNext} disabled={currentAnswer.length === 0}>
              Next
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          ) : (
            <Button
              onClick={handleSubmit}
              disabled={currentAnswer.length === 0 || submitting}
            >
              {submitting ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                  Processing...
                </>
              ) : (
                <>
                  <Check className="h-4 w-4 mr-1" />
                  Complete Quiz
                </>
              )}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};

export default StyleQuiz;
