import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { MainLayout } from '@/components/layout';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ArrowRight, Check, Sparkles, ShoppingBag, Loader2, AlertCircle, RefreshCw } from 'lucide-react';
import { createTransition } from '@/motion';

interface Question {
  id: string;
  text: string;
  type: string;
  options?: { id: string; text: string; value: any }[];
  min_value?: number;
  max_value?: number;
}

interface Product {
  id: string;
  name: string;
  description: string;
  category: string;
  price: number;
  image_url: string;
  tags: string[];
}

interface Recommendation {
  products: Product[];
  explanation: string;
}

export default function ChatbotPage() {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, any>>({});
  const [recommendations, setRecommendations] = useState<Recommendation | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    fetchQuestions();
  }, []);

  const fetchQuestions = async () => {
    try {
      setError(null);
      
      // Try backend API first
      try {
        const response = await fetch('/api/chatbot/questions');
        if (response.ok) {
          const data = await response.json();
          setQuestions(data);
          return;
        }
      } catch (backendError) {
        console.log('Backend unavailable, using mock data');
      }
      
      // Fallback to mock data
      const mockQuestions = [
        {
          id: "skin_type",
          text: "What is your skin tone?",
          type: "single_choice",
          options: [
            { id: "fair", text: "Fair", value: "fair" },
            { id: "light", text: "Light", value: "light" },
            { id: "medium", text: "Medium", value: "medium" },
            { id: "tan", text: "Tan", value: "tan" },
            { id: "deep", text: "Deep", value: "deep" },
          ],
        },
        {
          id: "gender",
          text: "What is your gender?",
          type: "single_choice",
          options: [
            { id: "male", text: "Male", value: "male" },
            { id: "female", text: "Female", value: "female" },
          ],
        },
        {
          id: "age",
          text: "What is your age group?",
          type: "single_choice",
          options: [
            { id: "18-24", text: "18-24", value: "young" },
            { id: "25-34", text: "25-34", value: "adult" },
            { id: "35-44", text: "35-44", value: "mature" },
            { id: "45+", text: "45+", value: "senior" },
          ],
        },
        {
          id: "occasion",
          text: "What occasion are you dressing for?",
          type: "single_choice",
          options: [
            { id: "casual", text: "Casual everyday", value: "casual" },
            { id: "work", text: "Work/Office", value: "work" },
            { id: "party", text: "Party/Event", value: "party" },
            { id: "formal", text: "Formal occasion", value: "formal" },
            { id: "sports", text: "Sports/Active", value: "sports" },
          ],
        },
        {
          id: "style_preference",
          text: "What style do you prefer?",
          type: "single_choice",
          options: [
            { id: "classic", text: "Classic", value: "classic" },
            { id: "modern", text: "Modern", value: "modern" },
            { id: "streetwear", text: "Streetwear", value: "streetwear" },
            { id: "elegant", text: "Elegant", value: "elegant" },
            { id: "casual", text: "Casual", value: "casual" },
          ],
        },
        {
          id: "budget",
          text: "What is your budget range?",
          type: "single_choice",
          options: [
            { id: "low", text: "Under $50", value: { min: 0, max: 50 } },
            { id: "medium", text: "$50-$150", value: { min: 50, max: 150 } },
            { id: "high", text: "$150-$300", value: { min: 150, max: 300 } },
            { id: "premium", text: "Over $300", value: { min: 300, max: 10000 } },
          ],
        },
      ];
      
      setQuestions(mockQuestions);
      
    } catch (err) {
      setError('Unable to load chatbot questions. Please try again.');
      console.error('Error fetching questions:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAnswer = (questionId: string, answer: any) => {
    setAnswers(prev => ({ ...prev, [questionId]: answer }));
  };

  const nextQuestion = () => {
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(prev => prev + 1);
    } else {
      submitAnswers();
    }
  };

  const prevQuestion = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(prev => prev - 1);
    }
  };

  const submitAnswers = async () => {
    setIsSubmitting(true);
    setError(null);
    try {
      // Try backend API first
      try {
        const response = await fetch('/api/chatbot/recommend', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ answers }),
        });
        if (response.ok) {
          const data = await response.json();
          setRecommendations(data);
          return;
        }
      } catch (backendError) {
        console.log('Backend unavailable, using mock recommendations');
      }
      
      // Fallback to mock recommendations
      const mockProducts = [
        {
          id: "prod-1",
          name: "Silk Blouse",
          description: "Elegant silk blouse perfect for formal occasions",
          category: "tops",
          price: 89.99,
          image_url: "https://images.unsplash.com/photo-1596755094514-f87e34085b2c?w=400&h=500&fit=crop",
          tags: ["elegant", "formal", "work"],
        },
        {
          id: "prod-2", 
          name: "Tailored Trousers",
          description: "Professional tailored trousers for office wear",
          category: "bottoms",
          price: 129.99,
          image_url: "https://images.unsplash.com/photo-1624378439575-d8705ad7ae80?w=400&h=500&fit=crop",
          tags: ["formal", "work", "classic"],
        },
        {
          id: "prod-3",
          name: "Midi Dress",
          description: "Versatile midi dress for any occasion",
          category: "dresses", 
          price: 149.99,
          image_url: "https://images.unsplash.com/photo-1595777457583-95e059d581b8?w=400&h=500&fit=crop",
          tags: ["elegant", "party", "casual"],
        },
        {
          id: "prod-4",
          name: "Leather Jacket",
          description: "Edgy leather jacket for street style",
          category: "outerwear",
          price: 299.99,
          image_url: "https://images.unsplash.com/photo-1544923246-77307dd628b8?w=400&h=500&fit=crop",
          tags: ["streetwear", "modern", "casual"],
        },
        {
          id: "prod-5",
          name: "Ankle Boots",
          description: "Stylish ankle boots for all seasons",
          category: "shoes",
          price: 119.99,
          image_url: "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?w=400&h=500&fit=crop",
          tags: ["casual", "modern", "elegant"],
        },
        {
          id: "prod-6",
          name: "Crossbody Bag",
          description: "Functional crossbody bag for daily use",
          category: "bags",
          price: 79.99,
          image_url: "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?w=400&h=500&fit=crop",
          tags: ["casual", "modern", "practical"],
        },
      ];
      
      // Generate personalized explanation
      const occasion = answers.occasion || "casual";
      const style = answers.style_preference || "classic";
      const budget = answers.budget || {};
      
      let explanation = `Based on your preferences for ${occasion} wear and ${style} style, I've selected these pieces for you. `;
      
      if (typeof budget === 'object' && budget.max) {
        if (budget.max < 100) {
          explanation += "These budget-friendly options offer great style without breaking the bank.";
        } else if (budget.max < 200) {
          explanation += "These mid-range pieces provide excellent quality and style.";
        } else {
          explanation += "These premium selections offer luxury and sophistication.";
        }
      } else {
        explanation += "These versatile pieces will work perfectly for your wardrobe!";
      }
      
      setRecommendations({
        products: mockProducts,
        explanation
      });
      
    } catch (err) {
      setError('Unable to get recommendations. Please try again.');
      console.error('Error submitting answers:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetChatbot = () => {
    setCurrentQuestionIndex(0);
    setAnswers({});
    setRecommendations(null);
    setError(null);
    fetchQuestions();
  };

  const currentQuestion = questions[currentQuestionIndex];
  const progress = ((currentQuestionIndex + 1) / questions.length) * 100;

  if (isLoading) {
    return (
      <MainLayout>
        <div className="container py-8 flex items-center justify-center min-h-[400px]">
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="text-center"
          >
            <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-accent" />
            <p className="text-muted-foreground">Loading your personal stylist...</p>
          </motion.div>
        </div>
      </MainLayout>
    );
  }

  if (error && !recommendations) {
    return (
      <MainLayout>
        <div className="container py-8 flex items-center justify-center min-h-[400px]">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center max-w-md"
          >
            <AlertCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
            <h2 className="text-xl font-semibold mb-2">Something went wrong</h2>
            <p className="text-muted-foreground mb-6">{error}</p>
            <Button onClick={resetChatbot} className="gap-2">
              <RefreshCw className="h-4 w-4" />
              Try Again
            </Button>
          </motion.div>
        </div>
      </MainLayout>
    );
  }

  if (recommendations) {
    return (
      <MainLayout>
        <div className="container py-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-8"
          >
            <h1 className="heading-hero mb-2">Your Personal Recommendations</h1>
            <p className="text-muted-foreground">{recommendations.explanation}</p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={createTransition({ delay: 0.2 })}
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8"
          >
            {recommendations.products.map((product, index) => (
              <motion.div
                key={product.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={createTransition({ delay: index * 0.1 })}
              >
                <Card className="group cursor-pointer hover:shadow-lg transition-all duration-300">
                  <div className="aspect-[4/5] relative overflow-hidden rounded-t-lg">
                    <img
                      src={product.image_url}
                      alt={product.name}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                  </div>
                  <CardContent className="p-4">
                    <h3 className="font-semibold mb-1 line-clamp-2">{product.name}</h3>
                    <p className="text-sm text-muted-foreground mb-2">{product.category}</p>
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-lg">${product.price}</span>
                      <Button size="sm" onClick={() => router.push(`/product/${product.id}`)}>
                        View
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={createTransition({ delay: 0.5 })}
            className="text-center"
          >
            <Button variant="outline" onClick={resetChatbot} className="gap-2">
              <RefreshCw className="h-4 w-4" />
              Start Over
            </Button>
          </motion.div>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="container py-8 max-w-2xl mx-auto">
        {/* Progress Bar */}
        <motion.div
          initial={{ opacity: 0, scaleX: 0 }}
          animate={{ opacity: 1, scaleX: 1 }}
          className="mb-8"
        >
          <div className="w-full bg-muted rounded-full h-2">
            <motion.div
              className="bg-accent h-2 rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={createTransition({ duration: 0.5 })}
            />
          </div>
          <p className="text-sm text-muted-foreground mt-2">
            Question {currentQuestionIndex + 1} of {questions.length}
          </p>
        </motion.div>

        {/* Question Card */}
        <AnimatePresence mode="wait">
          <motion.div
            key={currentQuestionIndex}
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -50 }}
            transition={createTransition({ duration: 0.3 })}
          >
            <Card className="mb-8">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-accent" />
                  {currentQuestion?.text}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {currentQuestion?.options ? (
                  <div className="grid grid-cols-1 gap-3">
                    {currentQuestion.options.map((option, index) => (
                      <motion.div
                        key={option.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={createTransition({ delay: index * 0.1 })}
                      >
                        <Button
                          variant={answers[currentQuestion.id] === option.value ? "default" : "outline"}
                          className="w-full justify-start h-auto p-4 text-left"
                          onClick={() => handleAnswer(currentQuestion.id, option.value)}
                        >
                          {answers[currentQuestion.id] === option.value && (
                            <Check className="h-4 w-4 mr-2 text-primary-foreground" />
                          )}
                          {option.text}
                        </Button>
                      </motion.div>
                    ))}
                  </div>
                ) : currentQuestion?.type === 'range' ? (
                  <div className="space-y-4">
                    <input
                      type="range"
                      min={currentQuestion.min_value || 0}
                      max={currentQuestion.max_value || 100}
                      value={answers[currentQuestion.id] || 50}
                      onChange={(e) => handleAnswer(currentQuestion.id, parseInt(e.target.value))}
                      className="w-full"
                    />
                    <p className="text-center text-sm text-muted-foreground">
                      Value: {answers[currentQuestion.id] || 50}
                    </p>
                  </div>
                ) : null}
              </CardContent>
            </Card>
          </motion.div>
        </AnimatePresence>

        {/* Navigation */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={createTransition({ delay: 0.3 })}
          className="flex justify-between"
        >
          <Button
            variant="outline"
            onClick={prevQuestion}
            disabled={currentQuestionIndex === 0}
            className="gap-2"
          >
            Previous
          </Button>

          <Button
            onClick={nextQuestion}
            disabled={!answers[currentQuestion?.id]}
            className="gap-2"
          >
            {isSubmitting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : currentQuestionIndex === questions.length - 1 ? (
              <>
                <ShoppingBag className="h-4 w-4" />
                Get Recommendations
              </>
            ) : (
              <>
                Next
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </Button>
        </motion.div>
      </div>
    </MainLayout>
  );
}
